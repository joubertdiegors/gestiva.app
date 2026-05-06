from django.contrib.auth.decorators import login_required, permission_required as _perm_required


def perm_required(perm):
    """Combina login_required + permission_required com raise_exception=True."""
    def decorator(view_func):
        view_func = _perm_required(perm, raise_exception=True)(view_func)
        view_func = login_required(view_func)
        return view_func
    return decorator
