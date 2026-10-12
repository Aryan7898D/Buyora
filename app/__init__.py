"""Buyora backend (Flask + MySQL).

`python run.py` starts one server that does two jobs:
  * serves the website (the ../frontend folder) at   http://localhost:5000
  * serves the JSON API under                        http://localhost:5000/api
"""
import json
import logging
import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from . import db

BASE_DIR = Path(__file__).resolve().parent.parent


def _mysql_config(data_dir):
    config = {
        "MYSQL_HOST": os.environ.get("BUYORA_DB_HOST", "127.0.0.1"),
        "MYSQL_PORT": os.environ.get("BUYORA_DB_PORT", "3306"),
        "MYSQL_USER": os.environ.get("BUYORA_DB_USER", "root"),
        "MYSQL_PASSWORD": os.environ.get("BUYORA_DB_PASSWORD", ""),
        "MYSQL_DATABASE": os.environ.get("BUYORA_DB_NAME", "buyora"),
    }
    credentials_file = Path(data_dir) / "mysql-config.json"
    if credentials_file.exists():
        try:
            stored = json.loads(credentials_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not read MySQL settings from {credentials_file}.") from exc
        if not isinstance(stored, dict):
            raise RuntimeError(f"MySQL settings in {credentials_file} must be a JSON object.")
        for key in config:
            env_key = "BUYORA_DB_" + key.removeprefix("MYSQL_")
            if not os.environ.get(env_key) and key in stored:
                config[key] = str(stored[key])
    return config


def _load_secret_key(data_dir):
    """Use BUYORA_SECRET_KEY if set, otherwise create one once and keep it in data/secret.key."""
    env = os.environ.get("BUYORA_SECRET_KEY")
    if env:
        return env
    key_file = Path(data_dir) / "secret.key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32))
    return key_file.read_text().strip()


def create_app(overrides=None):
    frontend_dir = BASE_DIR / "frontend"
    is_vercel = bool(os.environ.get("VERCEL"))
    app = Flask(
        __name__,
        static_folder=None if is_vercel else str(frontend_dir),
        static_url_path="" if not is_vercel else None,
    )

    data_dir = BASE_DIR / "data"
    app.config.update(
        DB_DRIVER=os.environ.get("BUYORA_DB_DRIVER", "mysql").lower(),
        **_mysql_config(data_dir),
        DATABASE=str(data_dir / "buyora-test.sqlite3"),
        RESET_DATABASE=False,
        CATALOG_FILE=str(BASE_DIR / "app" / "products.json"),
        ADMIN_EMAIL=os.environ.get("BUYORA_ADMIN_EMAIL", "admin@buyora.com"),
        ADMIN_PASSWORD=os.environ.get("BUYORA_ADMIN_PASSWORD", "admin123"),
        CORS_ORIGIN=os.environ.get("BUYORA_CORS_ORIGIN", "*"),
        MAX_CONTENT_LENGTH=1024 * 1024,  # 1 MB request limit
        JSON_SORT_KEYS=False,
    )
    if overrides:
        app.config.update(overrides)
    if app.config["DB_DRIVER"] not in ("mysql", "sqlite"):
        raise ValueError("BUYORA_DB_DRIVER must be either 'mysql' or 'sqlite'.")
    if is_vercel:
        required = {
            "BUYORA_DB_HOST": app.config["MYSQL_HOST"],
            "BUYORA_DB_PORT": app.config["MYSQL_PORT"],
            "BUYORA_DB_USER": app.config["MYSQL_USER"],
            "BUYORA_DB_PASSWORD": app.config["MYSQL_PASSWORD"],
            "BUYORA_DB_NAME": app.config["MYSQL_DATABASE"],
            "BUYORA_SECRET_KEY": os.environ.get("BUYORA_SECRET_KEY", ""),
            "BUYORA_ADMIN_PASSWORD": app.config["ADMIN_PASSWORD"],
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required Vercel environment variables: " + ", ".join(missing)
            )
    if not app.config.get("SECRET_KEY"):  # Flask pre-fills this key with None
        key_dir = Path(app.config["DATABASE"]).parent if app.config["DB_DRIVER"] == "sqlite" else data_dir
        app.config["SECRET_KEY"] = _load_secret_key(key_dir)

    if not app.config.get("TESTING"):
        logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    db.init_db(app)
    app.teardown_appcontext(db.close_db)

    from .routes import auth_routes, orders_routes, products_routes
    for module in (auth_routes, products_routes, orders_routes):
        app.register_blueprint(module.bp)

    # ----- CORS: lets the site call the API even if it is opened from another port -----
    @app.before_request
    def preflight():
        if request.method == "OPTIONS" and request.path.startswith("/api"):
            return "", 204

    @app.after_request
    def add_cors(response):
        if request.path.startswith("/api"):
            response.headers["Access-Control-Allow-Origin"] = app.config["CORS_ORIGIN"]
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Vary"] = "Origin"
        return response

    # ----- misc routes -----
    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "service": "buyora-backend-python"})

    @app.get("/js/config.js")
    def frontend_config():
        # When the site is served by this Python server, the API is on the same address ("/api"),
        # whatever port you run on. (The copy of config.js on disk is only used when the site is
        # opened from some other server, e.g. VS Code Live Server.)
        js = 'window.BUYORA_API_BASE = "/api";\n'
        return app.response_class(js, mimetype="application/javascript")

    if is_vercel:
        public_dir = BASE_DIR / "public"

        @app.get("/")
        def vercel_home():
            return send_from_directory(public_dir, "index.html")

        @app.get("/<path:filename>")
        def vercel_static_files(filename):
            return send_from_directory(public_dir, filename)
    else:
        @app.get("/")
        def home():
            return send_from_directory(frontend_dir, "index.html")

    # ----- JSON errors for /api, normal pages elsewhere -----
    def api_error(message, status):
        return jsonify({"error": message}), status

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api"):
            return api_error("Not found.", 404)
        return "Page not found", 404

    @app.errorhandler(405)
    def bad_method(_e):
        return api_error("Method not allowed.", 405)

    @app.errorhandler(413)
    def too_big(_e):
        return api_error("Request is too large.", 413)

    @app.errorhandler(500)
    def server_error(_e):
        if request.path.startswith("/api"):
            return api_error("Internal server error.", 500)
        return "Something went wrong.", 500

    return app
