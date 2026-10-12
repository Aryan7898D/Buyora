"""Run all checks with:   python -m unittest -v"""
import os
import tempfile
import unittest

from app import create_app

SHIP = {"name": "Aryan Test", "email": "aryan@example.com", "address": "22 MG Road",
        "city": "Delhi", "state": "DL", "zip": "110001", "country": "India", "phone": "9999999999"}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "DATABASE": os.path.join(self.tmp.name, "test.sqlite3"),
            "DB_DRIVER": "sqlite",
            "SECRET_KEY": "test-secret",
            "TESTING": True,
        })
        self.c = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    # --- helpers
    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def register(self, email="priya@example.com", password="secret123"):
        r = self.c.post("/api/auth/register", json={"name": "Priya", "email": email, "password": password})
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["token"]

    def admin_token(self):
        r = self.c.post("/api/auth/login", json={"email": "admin@buyora.com", "password": "admin123"})
        self.assertEqual(r.status_code, 200)
        return r.get_json()["token"]

    def stock(self, pid):
        return self.c.get(f"/api/products/{pid}").get_json()["product"]["stock"]

    # --- basics
    def test_health_and_frontend_are_served(self):
        self.assertTrue(self.c.get("/api/health").get_json()["ok"])
        for path in ("/", "/js/products.js", "/assets/products/p01.jpg"):
            with self.c.get(path) as r:
                self.assertEqual(r.status_code, 200, path)
        with self.c.get("/") as r:
            self.assertIn(b"Buyora", r.data)

    def test_config_js_points_at_same_server(self):
        with self.c.get("/js/config.js") as r:
            self.assertIn(b'"/api"', r.data)
            self.assertIn("javascript", r.mimetype)

    def test_backend_source_is_not_exposed(self):
        self.assertEqual(self.c.get("/run.py").status_code, 404)
        self.assertEqual(self.c.get("/app/auth.py").status_code, 404)
        self.assertEqual(self.c.get("/data/buyora.sqlite3").status_code, 404)

    def test_unknown_api_path_is_json_404(self):
        r = self.c.get("/api/nope")
        self.assertEqual(r.status_code, 404)
        self.assertIn("error", r.get_json())

    def test_cors_preflight(self):
        r = self.c.open("/api/orders", method="OPTIONS", headers={"Origin": "http://localhost:8080"})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertIn("Authorization", r.headers["Access-Control-Allow-Headers"])

    # --- products
    def test_catalog_matches_frontend_shape(self):
        data = self.c.get("/api/products").get_json()
        self.assertEqual(data["count"], 10)
        p = next(x for x in data["products"] if x["id"] == "p03")
        self.assertEqual(p["name"], "INNO3D GeForce RTX 5070 Ti iCHILL X3 Graphics Card")
        self.assertEqual((p["price"], p["oldPrice"], p["emi"], p["stock"]), (148499, 480000, 13424, 4))
        self.assertIsNone(p["rating"])
        self.assertEqual(p["images"], ["assets/products/p03.jpg"])
        self.assertIsInstance(p["features"], list)

    def test_filters_and_sorting(self):
        mice = self.c.get("/api/products?category=Mice").get_json()
        self.assertEqual({p["id"] for p in mice["products"]}, {"p05", "p06"})
        cheap = self.c.get("/api/products?maxPrice=3000&sort=price-asc").get_json()["products"]
        self.assertEqual([p["id"] for p in cheap], ["p05", "p07", "p08"])
        search = self.c.get("/api/products?q=alienware").get_json()
        self.assertEqual(search["count"], 2)
        best = self.c.get("/api/products?sort=discount").get_json()["products"][0]
        self.assertEqual(best["id"], "p05")  # 1999 vs 18000
        self.assertEqual(self.c.get("/api/products?maxPrice=abc").status_code, 400)
        cats = self.c.get("/api/products/categories").get_json()["categories"]
        self.assertIn("Monitors", cats)

    def test_product_404(self):
        self.assertEqual(self.c.get("/api/products/zzz").status_code, 404)

    # --- auth
    def test_register_login_me(self):
        token = self.register()
        me = self.c.get("/api/auth/me", headers=self.auth(token)).get_json()["user"]
        self.assertEqual((me["email"], me["role"]), ("priya@example.com", "customer"))
        self.assertNotIn("password_hash", me)
        r = self.c.post("/api/auth/login", json={"email": "PRIYA@example.com", "password": "secret123"})
        self.assertEqual(r.status_code, 200)

    def test_register_validation(self):
        self.register()
        dup = self.c.post("/api/auth/register", json={"name": "X", "email": "priya@example.com", "password": "secret123"})
        self.assertEqual(dup.status_code, 409)
        bad_email = self.c.post("/api/auth/register", json={"name": "X", "email": "nope", "password": "secret123"})
        self.assertEqual(bad_email.status_code, 400)
        short = self.c.post("/api/auth/register", json={"name": "X", "email": "a@b.co", "password": "123"})
        self.assertEqual(short.status_code, 400)
        self.assertEqual(self.c.post("/api/auth/register", json=[1, 2]).status_code, 400)

    def test_login_failures_and_bad_tokens(self):
        self.register()
        wrong = self.c.post("/api/auth/login", json={"email": "priya@example.com", "password": "wrongpass"})
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(self.c.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.c.get("/api/auth/me", headers=self.auth("garbage")).status_code, 401)

    # --- admin
    def test_admin_product_crud_and_roles(self):
        customer = self.register()
        admin = self.admin_token()
        new = {"id": "p99", "name": "Test Gadget", "category": "Monitors", "price": 999, "stock": 5}

        self.assertEqual(self.c.post("/api/products", json=new).status_code, 401)
        self.assertEqual(self.c.post("/api/products", json=new, headers=self.auth(customer)).status_code, 403)

        r = self.c.post("/api/products", json=new, headers=self.auth(admin))
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.c.post("/api/products", json=new, headers=self.auth(admin)).status_code, 409)
        bad = dict(new, id="p98", price="free")
        self.assertEqual(self.c.post("/api/products", json=bad, headers=self.auth(admin)).status_code, 400)

        r = self.c.put("/api/products/p99", json={"price": 1099, "stock": 7}, headers=self.auth(admin))
        self.assertEqual((r.get_json()["product"]["price"], r.get_json()["product"]["stock"]), (1099, 7))
        self.assertEqual(r.get_json()["product"]["name"], "Test Gadget")  # untouched fields stay

        self.assertEqual(self.c.delete("/api/products/p99", headers=self.auth(admin)).status_code, 204)
        self.assertEqual(self.c.delete("/api/products/p99", headers=self.auth(admin)).status_code, 404)

    # --- orders
    def test_order_prices_come_from_server(self):
        # p05 = 1999, p09 = 4999  -> subtotal 8997, shipping free, GST 18%
        r = self.c.post("/api/orders", json={
            "items": [{"productId": "p05", "qty": 2, "price": 1}, {"productId": "p09", "qty": 1}],
            "shipping": SHIP, "paymentMethod": "card"})
        self.assertEqual(r.status_code, 201, r.get_json())
        o = r.get_json()["order"]
        self.assertEqual(o["subtotal"], 8997)
        self.assertEqual(o["shipping"], 0)
        self.assertEqual(o["tax"], 1619.46)
        self.assertEqual(o["total"], 10616.46)
        self.assertEqual(o["status"], "pending")
        self.assertEqual(len(o["items"]), 2)
        self.assertEqual(self.stock("p05"), 23)
        self.assertEqual(self.stock("p09"), 24)

    def test_shipping_charge_and_coupon(self):
        # p07-like small cart: use p08 (2999)?? -> choose cheap item under threshold via admin product
        admin = self.admin_token()
        self.c.post("/api/products", headers=self.auth(admin),
                    json={"id": "tiny", "name": "Tiny", "category": "Mice", "price": 500, "stock": 3})
        r = self.c.post("/api/orders", json={"items": [{"productId": "tiny", "qty": 1}], "shipping": SHIP})
        o = r.get_json()["order"]
        self.assertEqual((o["subtotal"], o["shipping"], o["tax"], o["total"]), (500, 99, 90, 689))

        r = self.c.post("/api/orders", json={"items": [{"productId": "p05", "qty": 1}],
                                              "shipping": SHIP, "couponCode": "welcome20"})
        o = r.get_json()["order"]  # 1999 - 20% = 1599.2 ; GST 287.86 ; shipping free (cart >= 1999)
        self.assertEqual((o["discount"], o["shipping"], o["tax"], o["total"]), (399.8, 0, 287.86, 1887.06))

    def test_stock_and_validation_errors(self):
        base = {"shipping": SHIP}
        self.assertEqual(self.c.post("/api/orders", json={"items": [], **base}).status_code, 400)
        self.assertEqual(self.c.post("/api/orders", json={"items": [{"productId": "nope", "qty": 1}], **base}).status_code, 400)
        self.assertEqual(self.c.post("/api/orders", json={"items": [{"productId": "p05", "qty": 0}], **base}).status_code, 400)
        self.assertEqual(self.c.post("/api/orders", json={"items": [{"productId": "p05", "qty": "x"}], **base}).status_code, 400)
        self.assertEqual(self.c.post("/api/orders", json={"items": [{"productId": "p05", "qty": 1}], "shipping": {"name": "A"}}).status_code, 400)
        self.assertEqual(self.c.post("/api/orders", json={"items": "oops", **base}).status_code, 400)
        # p03 has 4 in stock
        too_many = self.c.post("/api/orders", json={"items": [{"productId": "p03", "qty": 5}], **base})
        self.assertEqual(too_many.status_code, 409)
        self.assertEqual(self.stock("p03"), 4)  # nothing was taken
        # same product on two lines is added up (3 + 2 > 4)
        split = self.c.post("/api/orders", json={"items": [{"productId": "p03", "qty": 3}, {"productId": "p03", "qty": 2}], **base})
        self.assertEqual(split.status_code, 409)
        self.assertEqual(self.stock("p03"), 4)

    def test_last_units_can_be_bought_then_sold_out(self):
        ok = self.c.post("/api/orders", json={"items": [{"productId": "p03", "qty": 4}], "shipping": SHIP})
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(self.stock("p03"), 0)
        again = self.c.post("/api/orders", json={"items": [{"productId": "p03", "qty": 1}], "shipping": SHIP})
        self.assertEqual(again.status_code, 409)

    def test_order_visibility_and_status(self):
        alice = self.register("alice@example.com")
        bob = self.register("bob@example.com")
        admin = self.admin_token()
        r = self.c.post("/api/orders", headers=self.auth(alice),
                        json={"items": [{"productId": "p07", "qty": 1}], "shipping": SHIP})
        oid = r.get_json()["order"]["id"]

        mine = self.c.get("/api/orders/mine", headers=self.auth(alice)).get_json()["orders"]
        self.assertEqual([o["id"] for o in mine], [oid])
        self.assertEqual(self.c.get("/api/orders/mine", headers=self.auth(bob)).get_json()["orders"], [])
        self.assertEqual(self.c.get(f"/api/orders/{oid}", headers=self.auth(alice)).status_code, 200)
        self.assertEqual(self.c.get(f"/api/orders/{oid}", headers=self.auth(bob)).status_code, 403)
        self.assertEqual(self.c.get(f"/api/orders/{oid}").status_code, 403)
        self.assertEqual(self.c.get(f"/api/orders/{oid}", headers=self.auth(admin)).status_code, 200)
        self.assertEqual(self.c.get("/api/orders/9999", headers=self.auth(admin)).status_code, 404)

        self.assertEqual(self.c.get("/api/orders/all", headers=self.auth(alice)).status_code, 403)
        self.assertEqual(len(self.c.get("/api/orders/all", headers=self.auth(admin)).get_json()["orders"]), 1)

        self.assertEqual(self.c.patch(f"/api/orders/{oid}/status", json={"status": "paid"}, headers=self.auth(alice)).status_code, 403)
        self.assertEqual(self.c.patch(f"/api/orders/{oid}/status", json={"status": "weird"}, headers=self.auth(admin)).status_code, 400)
        self.assertEqual(self.c.patch(f"/api/orders/{oid}/status", json={"status": "paid"}, headers=self.auth(admin)).status_code, 200)
        self.assertEqual(self.c.get(f"/api/orders/{oid}", headers=self.auth(admin)).get_json()["order"]["status"], "paid")

    def test_secret_key_is_created_automatically_and_reused(self):
        """Regression: with no SECRET_KEY given, one must be generated (and tokens must work)."""
        db_path = os.path.join(self.tmp.name, "auto.sqlite3")
        app1 = create_app({"DATABASE": db_path, "DB_DRIVER": "sqlite", "TESTING": True})
        self.assertTrue(app1.config["SECRET_KEY"])
        c1 = app1.test_client()
        token = c1.post("/api/auth/register", json={"name": "A", "email": "a@b.co", "password": "secret123"}).get_json()["token"]
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "secret.key")))
        app2 = create_app({"DATABASE": db_path, "DB_DRIVER": "sqlite", "TESTING": True})
        self.assertEqual(app2.config["SECRET_KEY"], app1.config["SECRET_KEY"])
        me = app2.test_client().get("/api/auth/me", headers=self.auth(token))
        self.assertEqual(me.status_code, 200)

    def test_data_survives_restart(self):
        token = self.register("keep@example.com")
        self.c.post("/api/orders", headers=self.auth(token),
                    json={"items": [{"productId": "p07", "qty": 1}], "shipping": SHIP})
        app2 = create_app({
            "DATABASE": self.app.config["DATABASE"],
            "DB_DRIVER": "sqlite",
            "SECRET_KEY": "test-secret",
            "TESTING": True,
        })
        c2 = app2.test_client()
        self.assertEqual(len(c2.get("/api/orders/mine", headers=self.auth(token)).get_json()["orders"]), 1)
        self.assertEqual(c2.get("/api/products").get_json()["count"], 10)  # not re-seeded twice
        self.assertEqual(c2.get("/api/products/p07").get_json()["product"]["stock"], 24)


if __name__ == "__main__":
    unittest.main()
