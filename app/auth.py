"""Login tokens + helpers that protect routes.

Tokens are signed with the app's SECRET_KEY (itsdangerous, installed with Flask),
so no extra libraries are needed. Passwords are hashed with werkzeug.
"""
from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .db import get_db

TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="buyora-auth")


def make_token(user):
    return _serializer().dumps({"id": user["id"]})


def public_user(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}


def _user_from_header():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        payload = _serializer().loads(header[7:], max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (payload.get("id"),)).fetchone()


def json_body():
    """The request's JSON body as a dict (empty dict if missing, broken, or not an object)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def error(message, status):
    return jsonify({"error": message}), status


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not request.headers.get("Authorization", "").startswith("Bearer "):
            return error("Missing or malformed Authorization header.", 401)
        user = _user_from_header()
        if user is None:
            return error("Invalid or expired token.", 401)
        g.user = user
        return view(*args, **kwargs)
    return wrapped


def optional_login(view):
    """Guests allowed; if a valid token is sent, g.user is filled in."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        g.user = _user_from_header()
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            return error("Admin access required.", 403)
        return view(*args, **kwargs)
    return wrapped
