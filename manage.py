"""Small admin helpers.

    python manage.py admin-password            (asks for a new admin password)
    python manage.py admin-password NEWPASS    (sets it directly)
    python manage.py stats                     (shows how many products / users / orders you have)
"""
import getpass
import sys

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db


def main(argv):
    if len(argv) < 2 or argv[1] not in ("admin-password", "stats"):
        print(__doc__)
        return 1

    app = create_app()
    with app.app_context():
        db = get_db()
        if argv[1] == "stats":
            for table in ("products", "users", "orders"):
                count = db.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
                print(f"{table:9}", count)
            return 0

        password = argv[2] if len(argv) > 2 else getpass.getpass("New admin password: ")
        if len(password) < 8:
            print("Please use at least 8 characters.")
            return 1
        cur = db.execute(
            "UPDATE users SET password_hash = ? WHERE role = 'admin'",
            (generate_password_hash(password, method="pbkdf2:sha256"),),
        )
        print(f"Admin password updated ({cur.rowcount} admin account).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
