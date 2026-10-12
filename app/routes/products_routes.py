"""/api/products  -  public catalog reads, admin-only writes"""
import json

from flask import Blueprint, jsonify, request

from ..auth import admin_required, error, json_body
from ..db import IntegrityError, get_db

bp = Blueprint("products", __name__, url_prefix="/api/products")

SORTS = {
    "price-asc": "price ASC",
    "price-desc": "price DESC",
    "name": "LOWER(name) ASC",
    "rating": "COALESCE(rating, 0) DESC",
    "discount": "CASE WHEN old_price IS NOT NULL AND old_price > 0 "
                "THEN (old_price - price) / old_price ELSE 0 END DESC",
}


def _loads(value, default):
    if value is None:
        return default
    try:
        return json.loads(value)
    except ValueError:
        return default


def serialize(row):
    """DB row -> the exact shape the frontend (js/products.js) expects."""
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "price": row["price"],
        "oldPrice": row["old_price"],
        "emi": row["emi"],
        "rating": row["rating"],
        "reviews": row["reviews"],
        "stock": row["stock"],
        "badge": row["badge"],
        "colors": _loads(row["colors"], None),
        "sizes": _loads(row["sizes"], None),
        "images": _loads(row["images"], []),
        "description": row["description"],
        "features": _loads(row["features"], []),
    }


def _number(value):
    """Return float(value) or None if it is not a real number."""
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@bp.get("")
def list_products():
    args = request.args
    sql, params = "SELECT * FROM products WHERE 1=1", []

    category = args.get("category")
    if category and category != "all":
        sql += " AND category = ?"
        params.append(category)
    for key, op in (("minPrice", ">="), ("maxPrice", "<="), ("minRating", ">=")):
        if args.get(key):
            number = _number(args[key])
            if number is None:
                return error(f"{key} must be a number.", 400)
            column = "rating" if key == "minRating" else "price"
            sql += f" AND {column} {op} ?"
            params.append(number)
    if args.get("q"):
        like = f"%{args['q']}%"
        sql += " AND (name LIKE ? OR category LIKE ?)"
        params += [like, like]

    sql += " ORDER BY " + SORTS.get(args.get("sort"), "id ASC")
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"products": [serialize(r) for r in rows], "count": len(rows)})


@bp.get("/categories")
def categories():
    rows = get_db().execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return jsonify({"categories": [r["category"] for r in rows]})


@bp.get("/<product_id>")
def get_product(product_id):
    row = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        return error("Product not found.", 404)
    return jsonify({"product": serialize(row)})


def _dump(value):
    return json.dumps(value) if value is not None else None


@bp.post("")
@admin_required
def create_product():
    p = json_body()
    if not p.get("id") or not p.get("name") or not p.get("category"):
        return error("id, name, category, and price are required.", 400)
    price = _number(p.get("price"))
    if price is None or price < 0:
        return error("price must be a positive number.", 400)
    stock = p.get("stock", 0)
    if not isinstance(stock, int) or isinstance(stock, bool) or stock < 0:
        return error("stock must be a whole number, 0 or more.", 400)

    db = get_db()
    try:
        db.execute(
            """INSERT INTO products (id, name, category, price, old_price, emi, rating, reviews,
                                     stock, badge, colors, sizes, images, description, features)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(p["id"]), p["name"], p["category"], price, p.get("oldPrice"), p.get("emi"),
             p.get("rating"), p.get("reviews") or 0, stock, p.get("badge"),
             _dump(p.get("colors")), _dump(p.get("sizes")), json.dumps(p.get("images") or []),
             p.get("description") or "", json.dumps(p.get("features") or [])),
        )
    except IntegrityError:
        return error("A product with that id already exists.", 409)
    row = db.execute("SELECT * FROM products WHERE id = ?", (p["id"],)).fetchone()
    return jsonify({"product": serialize(row)}), 201


@bp.put("/<product_id>")
@admin_required
def update_product(product_id):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        return error("Product not found.", 404)

    p = json_body()
    price = row["price"] if "price" not in p else _number(p["price"])
    if price is None or price < 0:
        return error("price must be a positive number.", 400)
    stock = p.get("stock", row["stock"])
    if not isinstance(stock, int) or isinstance(stock, bool) or stock < 0:
        return error("stock must be a whole number, 0 or more.", 400)

    def pick(key, column, encode=None):
        if key in p:
            return encode(p[key]) if encode else p[key]
        return row[column]

    db.execute(
        """UPDATE products SET name=?, category=?, price=?, old_price=?, emi=?, rating=?, reviews=?,
                               stock=?, badge=?, colors=?, sizes=?, images=?, description=?, features=?
           WHERE id=?""",
        (pick("name", "name"), pick("category", "category"), price,
         pick("oldPrice", "old_price"), pick("emi", "emi"), pick("rating", "rating"),
         pick("reviews", "reviews"), stock, pick("badge", "badge"),
         pick("colors", "colors", _dump), pick("sizes", "sizes", _dump),
         pick("images", "images", json.dumps), pick("description", "description"),
         pick("features", "features", json.dumps), product_id),
    )
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify({"product": serialize(row)})


@bp.delete("/<product_id>")
@admin_required
def delete_product(product_id):
    try:
        cur = get_db().execute("DELETE FROM products WHERE id = ?", (product_id,))
    except IntegrityError:
        return error("This product is part of existing orders, so it can't be deleted. "
                     "Set its stock to 0 instead.", 409)
    if cur.rowcount == 0:
        return error("Product not found.", 404)
    return "", 204
