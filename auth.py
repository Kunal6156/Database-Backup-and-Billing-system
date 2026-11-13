"""Authentication helpers: password hashing, CSRF protection, login lockout, role decorators."""
import hmac
import os
import secrets
import time
from functools import wraps

from flask import abort, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

MAX_FAILS = 5          # wrong passwords allowed ...
LOCK_SECONDS = 300     # ... before the account is locked for this long
MIN_PASSWORD_LEN = 8
_fails = {}            # username(lower) -> [count, locked_until_timestamp]

# A real hash of a random string, used so "unknown user" takes as long as "wrong password".
_DUMMY_HASH = None


def hash_password(password):
    method = os.environ.get("GN_PW_HASH_METHOD", "scrypt")
    try:
        return generate_password_hash(password, method=method)
    except (ValueError, AttributeError):  # Python built without scrypt
        return generate_password_hash(password, method="pbkdf2:sha256")


def verify_password(stored_hash, password):
    global _DUMMY_HASH
    if stored_hash is None:
        if _DUMMY_HASH is None:
            _DUMMY_HASH = hash_password(secrets.token_hex(8))
        check_password_hash(_DUMMY_HASH, password)
        return False
    return check_password_hash(stored_hash, password)


def validate_new_password(password):
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    if password.lower() == password and password.isalpha():
        raise ValueError("Use a mix of letters and numbers or symbols.")


# ---------------- login lockout ----------------
def is_locked(username):
    entry = _fails.get(username.lower())
    return bool(entry and entry[1] > time.time())


def register_failure(username):
    entry = _fails.setdefault(username.lower(), [0, 0])
    entry[0] += 1
    if entry[0] >= MAX_FAILS:
        entry[1] = time.time() + LOCK_SECONDS
        entry[0] = 0


def clear_failures(username):
    _fails.pop(username.lower(), None)


def reset_lockouts():  # used by tests
    _fails.clear()


# ---------------- CSRF ----------------
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def check_csrf():
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    expected = session.get("csrf", "")
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400, "Your form expired or is invalid. Go back, refresh the page and try again.")


# ---------------- roles ----------------
def safe_next(target):
    """Only allow redirects to paths inside this site (prevents open-redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("dashboard")


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if g.get("user") is None:
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return fn(*a, **kw)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if g.get("user") is None:
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        if g.user["role"] != "admin":
            abort(403)
        return fn(*a, **kw)
    return wrapper
