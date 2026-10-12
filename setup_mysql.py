"""Create Buyora's MySQL database and a dedicated local app account."""
import getpass
import json
import re
import secrets
import sys

import mysql.connector

from app import BASE_DIR

DATABASE = "buyora"
APP_HOST = "127.0.0.1"
CONFIG_PATH = BASE_DIR / "data" / "mysql-config.json"


def _load_or_create_app_credentials():
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not read saved settings from {CONFIG_PATH}.") from exc
        if not isinstance(config, dict):
            raise RuntimeError(f"Saved settings in {CONFIG_PATH} must be a JSON object.")
        user = config.get("MYSQL_USER")
        password = config.get("MYSQL_PASSWORD")
        if not isinstance(user, str) or not re.fullmatch(r"[a-zA-Z0-9_]+", user):
            raise RuntimeError(f"Saved app username in {CONFIG_PATH} is invalid.")
        if not isinstance(password, str) or not password:
            raise RuntimeError(f"Saved app password in {CONFIG_PATH} is missing.")
        return user, password
    return "buyora_app_" + secrets.token_hex(4), secrets.token_urlsafe(32)


def main():
    host = input("MySQL host [127.0.0.1]: ").strip() or "127.0.0.1"
    port_text = input("MySQL port [3306]: ").strip() or "3306"
    admin_user = input("MySQL admin user [root]: ").strip() or "root"
    admin_password = getpass.getpass("MySQL admin password (input hidden): ")
    try:
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print("MySQL port must be a number between 1 and 65535.", file=sys.stderr)
        return 1

    try:
        app_user, app_password = _load_or_create_app_credentials()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            autocommit=True,
        )
        cursor = connection.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DATABASE}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(
            f"CREATE USER IF NOT EXISTS '{app_user}'@'{APP_HOST}' IDENTIFIED BY %s",
            (app_password,),
        )
        cursor.execute(
            f"ALTER USER '{app_user}'@'{APP_HOST}' IDENTIFIED BY %s",
            (app_password,),
        )
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{DATABASE}`.* TO '{app_user}'@'{APP_HOST}'")
        cursor.close()
        connection.close()
    except mysql.connector.Error as exc:
        print(
            f"MySQL setup failed ({exc.__class__.__name__}). Check the server, "
            "admin username/password, and the admin account's CREATE USER/CREATE "
            "DATABASE privileges.",
            file=sys.stderr,
        )
        return 1

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "MYSQL_HOST": host,
        "MYSQL_PORT": str(port),
        "MYSQL_USER": app_user,
        "MYSQL_PASSWORD": app_password,
        "MYSQL_DATABASE": DATABASE,
    }
    temporary_path = CONFIG_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    temporary_path.replace(CONFIG_PATH)
    print(f"MySQL database '{DATABASE}' and app account are ready.")
    print(f"Local credentials saved to {CONFIG_PATH}; this file is ignored by Git.")
    print("Now run: python run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
