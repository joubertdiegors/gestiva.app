"""
Formatter de logs em JSON estruturado (Sprint 5).

Ativado em produção via `LOG_FORMAT=json` no .env. Pensado para futuro
ingestão em Loki/CloudWatch sem reformatar nada.

Inclui automaticamente o `request_id` corrente (vindo do middleware de
auditoria) quando existe — assim qualquer linha de log liga-se ao
`X-Request-ID` da resposta HTTP e ao Sentry event.
"""
import json
import logging
import time


class JSONFormatter(logging.Formatter):
    BASE_KEYS = (
        'name', 'levelname', 'pathname', 'lineno', 'module',
        'funcName', 'process', 'thread', 'threadName',
    )

    def format(self, record):
        from audit.middleware import get_request_context

        payload = {
            'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
            'module': record.module,
            'line': record.lineno,
        }

        try:
            ctx = get_request_context()
        except Exception:
            ctx = {}
        request_id = ctx.get('request_id') or ''
        if request_id:
            payload['request_id'] = request_id

        if record.exc_info:
            payload['exc'] = self.formatException(record.exc_info)

        # `extra=` em logger.info(...) cai em record.__dict__; copia chaves
        # adicionais não-built-in.
        for key, value in record.__dict__.items():
            if key in payload or key in self.BASE_KEYS or key.startswith('_'):
                continue
            if key in ('msg', 'args', 'exc_info', 'exc_text', 'stack_info',
                       'created', 'msecs', 'relativeCreated', 'levelno',
                       'message', 'filename', 'taskName'):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)

        return json.dumps(payload, ensure_ascii=False)
