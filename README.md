# Curio Store

Full-stack online store. Browse products, search by category, open product detail slides, fill a shopping bag with festive (5%) and bulk (extra 10% for 5+ items) discounts, and place an order.

- **Frontend:** `static/index.html` (HTML, CSS, JavaScript)
- **Backend:** Python + FastAPI (`curio_store_api.py`), pricing rules in `curio_pricing.py`, product catalogue in `products.json`
- **Orders:** saved to a SQLite database. The server recalculates every price and discount itself and never trusts the page's numbers.
- **Tests:** `test_curio_store.py`
- Demo store: no payment is taken, and only the customer's name is stored with an order.

## Folder layout
```
images/              your product photos (keep the folder you already have)
static/index.html    the store page
products.json        the products (edit this to add or change items)
curio_pricing.py     discount rules
curio_store_api.py   the server
test_curio_store.py  tests
requirements.txt, Dockerfile
```

## Run locally
```
pip install -r requirements.txt
pytest
uvicorn curio_store_api:app --reload
```
Then open http://127.0.0.1:8000 in your browser.

## Deploy free (one public link)
On render.com choose New, then Web Service, pick this repo, set the runtime to **Docker** and the instance type to **Free**.

Optional: under Environment add `ADMIN_KEY` with a secret word of your choice. Then you can read the saved orders:
```
curl -H "x-admin-key: YOUR_SECRET" https://YOUR-APP.onrender.com/api/admin/orders
```

Note: on the free plan the orders database is wiped whenever the service restarts or is redeployed. To keep orders permanently, move them to an external database.

## API
- `GET /api/products?category=Laptops&q=gaming`
- `GET /api/products/{id}`
- `POST /api/quote` with `{"items":[{"id":0,"qty":2}]}`
- `POST /api/orders` with `{"name":"Asha","items":[{"id":0,"qty":2}]}`
- `GET /api/admin/orders` (needs the `x-admin-key` header)
- `GET /api/health`
