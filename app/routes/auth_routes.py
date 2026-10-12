"""/api/auth  -  register, login, me"""
import re

from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import error, json_body, login_required, make_token, public_user
from ..db import IntegrityError, get_db

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@bp.post("/register")
def register():
    data = json_body()
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not name or not email or not password:
        return error("name, email, and password are all required.", 400)
    if not EMAIL_RE.match(email):
        return error("Please provide a valid email address.", 400)
    if len(password) < 6:
        return error("Password must be at least 6 characters.", 400)

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?, 'customer')",
            (name, email, generate_password_hash(password, method="pbkdf2:sha256")),
        )
    except IntegrityError:
        return error("An account with that email already exists.", 409)

    user = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify({"token": make_token(user), "user": public_user(user)}), 201


@bp.post("/login")
def login():
    data = json_body()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    if not email or not password:
        return error("email and password are required.", 400)

    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return error("Invalid email or password.", 401)
    return jsonify({"token": make_token(user), "user": public_user(user)})


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": public_user(g.user)})
