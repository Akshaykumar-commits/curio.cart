import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["ADMIN_KEY"] = "secret"

import pytest
from fastapi.testclient import TestClient

from curio_pricing import PRODUCTS, price_cart
from curio_store_api import app

client = TestClient(app)


def test_small_cart_gets_festive_only():
    r = price_cart([(0, 1)])
    assert r["subtotal"] == 1499 and r["bulk"] == 0
    assert r["festive"] == 74.95 and r["total"] == 1424.05


def test_five_items_get_bulk_discount():
    r = price_cart([(0, 3), (1, 2)])
    assert r["items_count"] == 5 and r["bulk"] > 0
    assert r["total"] < r["subtotal"] * 0.95


def test_unknown_product_rejected():
    with pytest.raises(ValueError):
        price_cart([(999, 1)])


def test_health_and_products():
    assert client.get("/api/health").json()["products"] == len(PRODUCTS)
    laptops = client.get("/api/products", params={"category": "Laptops"}).json()
    assert laptops and all(p["cat"] == "Laptops" for p in laptops)
    assert all("phone" in p["name"].lower() for p in client.get("/api/products", params={"q": "phone"}).json())
    assert client.get("/api/products/999").status_code == 404


def test_order_flow_and_admin():
    body = {"name": "Asha", "items": [{"id": 0, "qty": 3}, {"id": 1, "qty": 2}]}
    r = client.post("/api/orders", json=body)
    assert r.status_code == 200
    assert r.json()["total"] == price_cart([(0, 3), (1, 2)])["total"]
    assert client.get("/api/admin/orders").status_code == 403
    orders = client.get("/api/admin/orders", headers={"x-admin-key": "secret"}).json()
    assert any(o["name"] == "Asha" for o in orders)


@pytest.mark.parametrize("body", [
    {"name": "A", "items": [{"id": 0, "qty": 0}]},
    {"name": "   ", "items": [{"id": 0, "qty": 1}]},
    {"name": "A", "items": [{"id": 999, "qty": 1}]},
    {"name": "A", "items": []},
])
def test_bad_orders_rejected(body):
    assert client.post("/api/orders", json=body).status_code == 422
