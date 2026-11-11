"""Curio Store backend (FastAPI): products, price quotes, orders. Also serves the web page."""
import hmac
import json
import os
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from curio_pricing import BY_ID, PRODUCTS, price_cart

ROOT = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", str(ROOT / "curio.db"))
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")  # set this to be able to read orders
RATE_LIMIT, RATE_WINDOW = 10, 60             # orders per seconds, per visitor

app = FastAPI(title="Curio Store")
_hits = defaultdict(deque)


class Item(BaseModel):
    id: int
    qty: int = Field(ge=1, le=20)


class Cart(BaseModel):
    items: list[Item] = Field(min_length=1, max_length=50)


class OrderIn(Cart):
    name: str = Field(min_length=1, max_length=60)


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


with closing(db()) as _con:
    _con.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, name TEXT, items TEXT,
        items_count INTEGER, subtotal REAL, festive REAL, bulk REAL, total REAL)""")
    _con.commit()


def _price(cart: Cart):
    try:
        return price_cart([(i.id, i.qty) for i in cart.items])
    except ValueError as e:
        raise HTTPException(422, str(e))


def _check_rate(request: Request):
    ip = (request.headers.get("x-forwarded-for") or request.client.host or "?").split(",")[0].strip()
    now, q = time.time(), _hits[ip]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Too many orders. Please wait a minute and try again.")
    q.append(now)


@app.get("/api/health")
def health():
    imgs = ROOT / "static" / "images"
    count = len(list(imgs.glob("*.jpg"))) if imgs.is_dir() else 0
    return {"status": "ok", "products": len(PRODUCTS), "images": count}


@app.get("/api/products")
def products(category: str = "", q: str = ""):
    q = q.strip().lower()
    return [p for p in PRODUCTS
            if (category in ("", "All") or p["cat"] == category) and q in p["name"].lower()]


@app.get("/api/products/{pid}")
def product(pid: int):
    p = BY_ID.get(pid)
    if not p:
        raise HTTPException(404, "Product not found")
    return p


@app.post("/api/quote")
def quote(cart: Cart):
    return _price(cart)


@app.post("/api/orders")
def create_order(order: OrderIn, request: Request):
    _check_rate(request)
    name = order.name.strip()
    if not name:
        raise HTTPException(422, "Please enter your name.")
    r = _price(order)  # the server always recalculates prices; the page's numbers are never trusted
    with closing(db()) as con:
        cur = con.execute(
            "INSERT INTO orders(created,name,items,items_count,subtotal,festive,bulk,total) VALUES(?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), name, json.dumps(r["lines"]), r["items_count"],
             r["subtotal"], r["festive"], r["bulk"], r["total"]))
        con.commit()
        oid = cur.lastrowid
    return {"id": oid, "name": name, **{k: r[k] for k in ("items_count", "subtotal", "festive", "bulk", "total")}}


@app.get("/api/admin/orders")
def admin_orders(x_admin_key: str = Header("")):
    if not ADMIN_KEY or not hmac.compare_digest(x_admin_key, ADMIN_KEY):
        raise HTTPException(403, "Forbidden")
    with closing(db()) as con:
        rows = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 200").fetchall()
    return [{**dict(r), "items": json.loads(r["items"])} for r in rows]


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
