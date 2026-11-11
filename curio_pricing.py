"""Curio Store pricing rules and product catalogue (plain Python, no web code)."""
import json
from pathlib import Path

PRODUCTS = json.loads((Path(__file__).parent / "products.json").read_text(encoding="utf-8"))
BY_ID = {p["id"]: p for p in PRODUCTS}

FESTIVE_RATE = 0.05    # 5% off every order
BULK_RATE = 0.10       # extra 10% off (after the festive offer)...
BULK_MIN_ITEMS = 5     # ...when the order has 5 or more items


def price_cart(items):
    """items: list of (product_id, quantity). Raises ValueError for an unknown product."""
    lines, subtotal, count = [], 0, 0
    for pid, qty in items:
        p = BY_ID.get(pid)
        if p is None:
            raise ValueError(f"Unknown product id {pid}")
        lines.append({"id": pid, "name": p["name"], "price": p["price"], "qty": qty,
                      "line_total": p["price"] * qty})
        subtotal += p["price"] * qty
        count += qty
    festive = subtotal * FESTIVE_RATE
    bulk = (subtotal - festive) * BULK_RATE if count >= BULK_MIN_ITEMS else 0
    return {"lines": lines, "items_count": count, "subtotal": subtotal,
            "festive": round(festive, 2), "bulk": round(bulk, 2),
            "total": round(subtotal - festive - bulk, 2)}
