import uuid
from threading import local

_thread_locals = local()


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


def get_current_user():
    user = getattr(_thread_locals, 'user', None)
    if user and user.is_authenticated:
        return user
    return None


def get_request_context():
    return {
        'ip': getattr(_thread_locals, 'ip', None),
        'user_agent': getattr(_thread_locals, 'user_agent', ''),
        'request_id': getattr(_thread_locals, 'request_id', ''),
    }


class CurrentUserMiddleware:
    """
    Captura o utilizador autenticado e o contexto do request (IP, User-Agent,
    request_id) para que os signals de auditoria possam preservar quem fez a
    alteração e em que sessão de pedido. Sem isto o AuditLog é cego em produção.
    """

    HEADER_REQUEST_ID = 'HTTP_X_REQUEST_ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = request.user
        _thread_locals.ip = _client_ip(request)
        _thread_locals.user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:500]
        _thread_locals.request_id = (
            request.META.get(self.HEADER_REQUEST_ID) or uuid.uuid4().hex
        )
        try:
            response = self.get_response(request)
            response['X-Request-ID'] = _thread_locals.request_id
            return response
        finally:
            _thread_locals.user = None
            _thread_locals.ip = None
            _thread_locals.user_agent = ''
            _thread_locals.request_id = ''
