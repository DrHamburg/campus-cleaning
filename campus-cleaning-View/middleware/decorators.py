from functools import wraps
from flask import session, redirect, url_for, render_template


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_page"))
        return fn(*args, **kwargs)
    return wrapper


def require_role(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login_page"))
            if session.get("role") != role:
                return render_template("error.html", message="Forbidden: you don't have permission to view this page."), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
