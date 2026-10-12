"""Database layer: MySQL in production, SQLite only for isolated tests."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import mysql.connector
from flask import current_app, g
from werkzeug.security import generate_password_hash

MYSQL_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('customer','admin') NOT NULL DEFAULT 'customer',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id VARCHAR(100) NOT NULL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(100) NOT NULL,
        price DOUBLE NOT NULL,
        old_price DOUBLE,
        emi DOUBLE,
        rating DOUBLE,
        reviews INT NOT NULL DEFAULT 0,
        stock INT NOT NULL DEFAULT 0,
        badge VARCHAR(255),
        colors TEXT,
        sizes TEXT,
        images TEXT,
        description TEXT,
        features TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_products_category (category)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT UNSIGNED,
        status ENUM('pending','paid','fulfilled','cancelled') NOT NULL DEFAULT 'pending',
        payment_method VARCHAR(50) NOT NULL DEFAULT 'cod',
        subtotal DOUBLE NOT NULL,
        discount DOUBLE NOT NULL DEFAULT 0,
        shipping DOUBLE NOT NULL DEFAULT 0,
        tax DOUBLE NOT NULL DEFAULT 0,
        total DOUBLE NOT NULL,
        shipping_name VARCHAR(255),
        shipping_email VARCHAR(255),
        shipping_address TEXT,
        shipping_city VARCHAR(255),
        shipping_state VARCHAR(255),
        shipping_zip VARCHAR(50),
        shipping_country VARCHAR(100),
        shipping_phone VARCHAR(100),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_orders_user (user_id),
        CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        order_id BIGINT UNSIGNED NOT NULL,
        product_id VARCHAR(100) NOT NULL,
        name VARCHAR(255) NOT NULL,
        price DOUBLE NOT NULL,
        qty INT NOT NULL,
        color VARCHAR(255),
        size VARCHAR(255),
        INDEX idx_order_items_order (order_id),
        CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
)
IntegrityError = (mysql.connector.IntegrityError, sqlite3.IntegrityError)

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer','admin')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL,
    old_price REAL, emi REAL, rating REAL, reviews INTEGER NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0, badge TEXT, colors TEXT, sizes TEXT, images TEXT,
    description TEXT, features TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','fulfilled','cancelled')),
    payment_method TEXT NOT NULL DEFAULT 'cod', subtotal REAL NOT NULL,
    discount REAL NOT NULL DEFAULT 0, shipping REAL NOT NULL DEFAULT 0,
    tax REAL NOT NULL DEFAULT 0, total REAL NOT NULL, shipping_name TEXT,
    shipping_email TEXT, shipping_address TEXT, shipping_city TEXT, shipping_state TEXT,
    shipping_zip TEXT, shipping_country TEXT, shipping_phone TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id), name TEXT NOT NULL,
    price REAL NOT NULL, qty INTEGER NOT NULL, color TEXT, size TEXT
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
"""


class MySQLDatabase:
    """Small DB-API adapter retaining the app's sqlite-style execute interface."""

    supports_for_update = True

    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(sql.replace("?", "%s"), params)
        return cursor

    def executemany(self, sql, rows):
        cursor = self.connection.cursor()
        cursor.executemany(sql.replace("?", "%s"), rows)
        return cursor

    def close(self):
        self.connection.close()


class SQLiteDatabase:
    supports_for_update = False

    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        return self.connection.execute(sql, params)

    def executemany(self, sql, rows):
        return self.connection.executemany(sql, rows)

    def executescript(self, sql):
        return self.connection.executescript(sql)

    def close(self):
        self.connection.close()


def _connect_mysql(config):
    try:
        connection = mysql.connector.connect(
            host=config["MYSQL_HOST"],
            port=int(config["MYSQL_PORT"]),
            user=config["MYSQL_USER"],
            password=config["MYSQL_PASSWORD"],
            database=config["MYSQL_DATABASE"],
            autocommit=True,
        )
    except mysql.connector.Error as exc:
        raise RuntimeError(
            "Could not connect to MySQL. Check that the server is running, the "
            "configured database exists, and BUYORA_DB_HOST/PORT/USER/PASSWORD/NAME "
            "are correct."
        ) from exc
    return MySQLDatabase(connection)


def _connect_sqlite(path):
    connection = sqlite3.connect(path, isolation_level=None, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return SQLiteDatabase(connection)


def _connect(config):
    if config["DB_DRIVER"] == "sqlite":
        if not config.get("TESTING"):
            raise RuntimeError("SQLite is available only when TESTING=True.")
        path = Path(config["DATABASE"])
        path.parent.mkdir(parents=True, exist_ok=True)
        return _connect_sqlite(path)
    return _connect_mysql(config)


def get_db():
    if "db" not in g:
        g.db = _connect(current_app.config)
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@contextmanager
def transaction(conn):
    """Run an order and its stock updates as one transaction."""
    if conn.supports_for_update:
        conn.connection.start_transaction()
    else:
        conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if conn.supports_for_update:
            conn.connection.rollback()
        else:
            conn.execute("ROLLBACK")
        raise
    else:
        if conn.supports_for_update:
            conn.connection.commit()
        else:
            conn.execute("COMMIT")


def _product_values(product):
    def encode(value):
        return json.dumps(value) if value is not None else None

    return (
        product["id"], product["name"], product["category"], product["price"],
        product.get("oldPrice"), product.get("emi"), product.get("rating"),
        product.get("reviews") or 0, product.get("stock") or 0, product.get("badge"),
        encode(product.get("colors")), encode(product.get("sizes")),
        json.dumps(product.get("images") or []), product.get("description") or "",
        json.dumps(product.get("features") or []),
    )


def _seed_database(app, conn):
    if conn.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"] == 0:
        catalog = json.loads(Path(app.config["CATALOG_FILE"]).read_text(encoding="utf-8"))
        conn.executemany(
            """INSERT INTO products (id, name, category, price, old_price, emi, rating, reviews,
                                     stock, badge, colors, sizes, images, description, features)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [_product_values(product) for product in catalog],
        )
        app.logger.info("Loaded %d products into the database.", len(catalog))

    if conn.execute(
        "SELECT COUNT(*) AS count FROM users WHERE role = 'admin'"
    ).fetchone()["count"] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?, 'admin')",
            (
                "Buyora Admin",
                app.config["ADMIN_EMAIL"],
                generate_password_hash(app.config["ADMIN_PASSWORD"], method="pbkdf2:sha256"),
            ),
        )
        app.logger.warning(
            "Created admin account %s - change the password before going live!",
            app.config["ADMIN_EMAIL"],
        )


def init_db(app):
    """Create schema and seed the catalog/admin account when needed."""
    conn = _connect(app.config)
    try:
        if app.config.get("RESET_DATABASE"):
            for table in ("order_items", "orders", "products", "users"):
                conn.execute(f"DROP TABLE IF EXISTS {table}")

        if app.config["DB_DRIVER"] == "sqlite":
            conn.executescript(SQLITE_SCHEMA)
        else:
            for statement in MYSQL_SCHEMA:
                conn.execute(statement)
        _seed_database(app, conn)
    finally:
        conn.close()
