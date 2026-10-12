"""/api/orders  -  checkout (prices are ALWAYS taken from the database, never from the browser)"""
from collections import defaultdict

from flask import Blueprint, g, jsonify, request

from ..auth import admin_required, error, json_body, login_required, optional_login
from ..db import get_db, transaction

bp = Blueprint("orders", __name__, url_prefix="/api/orders")

# Store rules (rupees). Keep these in sync with cart.html / checkout.html.
SHIPPING_FLAT = 99          # Rs 99 shipping ...
FREE_SHIP_THRESHOLD = 1999  # ... free when the cart is Rs 1,999 or more
GST_RATE = 0.18             # 18% GST
COUPONS = {"WELCOME20": 0.20}
MAX_QTY_PER_LINE = 100
STATUSES = ("pending", "paid", "fulfilled", "cancelled")


def _money(value):
    return round(value + 1e-9, 2)


def serialize_order(db, order):
    items = db.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order["id"],)).fetchall()
    return {
        "id": order["id"],
        "status": order["status"],
        "paymentMethod": order["payment_method"],
        "subtotal": order["subtotal"],
        "discount": order["discount"],
        "shipping": order["shipping"],
        "tax": order["tax"],
        "total": order["total"],
        "shipping_info": {
            "name": order["shipping_name"], "email": order["shipping_email"],
            "address": order["shipping_address"], "city": order["shipping_city"],
            "state": order["shipping_state"], "zip": order["shipping_zip"],
            "country": order["shipping_country"], "phone": order["shipping_phone"],
        },
        "items": [
            {"productId": i["product_id"], "name": i["name"], "price": i["price"],
             "qty": i["qty"], "color": i["color"], "size": i["size"]}
            for i in items
        ],
        "createdAt": order["created_at"],
    }


def _parse_lines(raw_items):
    """Validate the cart lines the browser sent. Returns (lines, error_message)."""
    if not isinstance(raw_items, list) or not raw_items:
        return None, "Order must include at least one item."
    lines = []
    for raw in raw_items:
        if not isinstance(raw, dict) or not raw.get("productId"):
            return None, "Every item needs a productId."
        try:
            qty = int(raw.get("qty", 1))
        except (TypeError, ValueError):
            return None, "Quantity must be a whole number."
        if qty < 1 or qty > MAX_QTY_PER_LINE:
            return None, f"Quantity must be between 1 and {MAX_QTY_PER_LINE}."
        lines.append({"productId": str(raw["productId"]), "qty": qty,
                      "color": raw.get("color") or None, "size": raw.get("size") or None})
    return lines, None


@bp.post("")
@optional_login
def create_order():
    data = json_body()
    lines, problem = _parse_lines(data.get("items"))
    if problem:
        return error(problem, 400)

    shipping = data.get("shipping")
    if not isinstance(shipping, dict):
        shipping = {}
    if not all(str(shipping.get(k) or "").strip() for k in ("name", "email", "address")):
        return error("Shipping name, email, and address are required.", 400)

    coupon = str(data.get("couponCode") or "").strip().upper()
    db = get_db()

    with transaction(db):
        # 1. look up every product and make sure there is enough stock (summing repeated lines)
        wanted = defaultdict(int)
        for line in lines:
            wanted[line["productId"]] += line["qty"]
        products = {}
        for product_id, qty in sorted(wanted.items()):
            lock = " FOR UPDATE" if db.supports_for_update else ""
            product = db.execute(
                "SELECT * FROM products WHERE id = ?" + lock, (product_id,)
            ).fetchone()
            if product is None:
                return error(f"Product {product_id} does not exist.", 400)
            if product["stock"] < qty:
                left = product["stock"]
                return error(f'Not enough stock for "{product["name"]}" (only {left} left).', 409)
            products[product_id] = product

        # 2. prices come from the database
        subtotal = sum(products[l["productId"]]["price"] * l["qty"] for l in lines)
        discount = subtotal * COUPONS.get(coupon, 0)
        shipping_cost = 0 if subtotal >= FREE_SHIP_THRESHOLD else SHIPPING_FLAT
        tax = (subtotal - discount) * GST_RATE
        total = subtotal - discount + shipping_cost + tax

        # 3. save the order and take the stock
        cur = db.execute(
            """INSERT INTO orders (user_id, status, payment_method, subtotal, discount, shipping, tax, total,
                                   shipping_name, shipping_email, shipping_address, shipping_city,
                                   shipping_state, shipping_zip, shipping_country, shipping_phone)
               VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (g.user["id"] if g.user else None, str(data.get("paymentMethod") or "cod"),
             _money(subtotal), _money(discount), _money(shipping_cost), _money(tax), _money(total),
             str(shipping["name"]).strip(), str(shipping["email"]).strip(), str(shipping["address"]).strip(),
             str(shipping.get("city") or ""), str(shipping.get("state") or ""),
             str(shipping.get("zip") or ""), str(shipping.get("country") or ""),
             str(shipping.get("phone") or "")),
        )
        order_id = cur.lastrowid
        for line in lines:
            product = products[line["productId"]]
            db.execute(
                "INSERT INTO order_items (order_id, product_id, name, price, qty, color, size) VALUES (?,?,?,?,?,?,?)",
                (order_id, product["id"], product["name"], product["price"],
                 line["qty"], line["color"], line["size"]),
            )
        for product_id, qty in wanted.items():
            db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, product_id))

    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return jsonify({"order": serialize_order(db, order)}), 201


@bp.get("/mine")
@login_required
def my_orders():
    db = get_db()
    rows = db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (g.user["id"],)).fetchall()
    return jsonify({"orders": [serialize_order(db, r) for r in rows]})


@bp.get("/all")
@admin_required
def all_orders():
    db = get_db()
    rows = db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return jsonify({"orders": [serialize_order(db, r) for r in rows]})


@bp.get("/<int:order_id>")
@optional_login
def get_order(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        return error("Order not found.", 404)
    is_owner = g.user is not None and order["user_id"] == g.user["id"]
    is_admin = g.user is not None and g.user["role"] == "admin"
    if not (is_owner or is_admin):
        return error("You don't have access to this order.", 403)
    return jsonify({"order": serialize_order(db, order)})


@bp.patch("/<int:order_id>/status")
@admin_required
def update_status(order_id):
    status = json_body().get("status")
    if status not in STATUSES:
        return error(f"status must be one of: {', '.join(STATUSES)}", 400)
    cur = get_db().execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    if cur.rowcount == 0:
        return error("Order not found.", 404)
    return jsonify({"ok": True})
