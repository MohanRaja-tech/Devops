import json
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

SERVICE_NAME = "backend"
DB_PATH = os.getenv("DB_PATH", "/data/mini_shop.db")

PRODUCTS = [
    {
        "id": 1,
        "name": "Aurora Headphones",
        "category": "Audio",
        "price": 129.0,
        "description": "Noise-cancelling wireless headphones for remote work and travel.",
    },
    {
        "id": 2,
        "name": "Nimbus Keyboard",
        "category": "Accessories",
        "price": 89.0,
        "description": "Mechanical keyboard with hot-swappable switches and soft backlight.",
    },
    {
        "id": 3,
        "name": "Orbit Desk Lamp",
        "category": "Office",
        "price": 54.0,
        "description": "Adjustable desk lamp with warm and cool lighting modes.",
    },
    {
        "id": 4,
        "name": "Pulse Smart Bottle",
        "category": "Lifestyle",
        "price": 39.0,
        "description": "Hydration tracker bottle with reminder notifications.",
    },
]


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                items_json TEXT NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_order_rows():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, customer_name, email, items_json, total, created_at FROM orders ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/")
def home():
    return jsonify(
        service=SERVICE_NAME,
        message="Backend catalog and order service is running.",
        routes=["/health", "/api/products", "/api/orders"],
    )


@app.get("/health")
def health():
    initialize_database()
    return jsonify(status="ok", service=SERVICE_NAME, database="ready", orders=len(get_order_rows()))


@app.get("/api/products")
def products():
    return jsonify(
        service=SERVICE_NAME,
        total=len(PRODUCTS),
        items=PRODUCTS,
    )


@app.get("/api/summary")
def summary():
    initialize_database()
    order_rows = get_order_rows()
    total_revenue = round(sum(float(row["total"]) for row in order_rows), 2)
    last_order = order_rows[0] if order_rows else None

    return jsonify(
        service=SERVICE_NAME,
        products=len(PRODUCTS),
        orders=len(order_rows),
        revenue=total_revenue,
        last_order=last_order,
    )


@app.route("/api/orders", methods=["GET", "POST"])
def orders():
    initialize_database()

    if request.method == "GET":
        items = get_order_rows()
        return jsonify(service=SERVICE_NAME, total=len(items), items=items)

    payload = request.get_json(force=True, silent=True) or {}
    customer_name = (payload.get("customer_name") or "").strip()
    email = (payload.get("email") or "").strip()
    items = payload.get("items") or []

    if not customer_name or not email or not items:
        return jsonify(error="customer_name, email, and items are required"), 400

    order_total = 0.0
    normalized_items = []
    product_lookup = {product["id"]: product for product in PRODUCTS}

    for item in items:
        product_id = int(item.get("id", 0))
        quantity = int(item.get("quantity", 0))
        product = product_lookup.get(product_id)
        if not product or quantity <= 0:
            return jsonify(error="invalid product item in order"), 400

        line_total = float(product["price"]) * quantity
        order_total += line_total
        normalized_items.append(
            {
                "id": product_id,
                "name": product["name"],
                "price": product["price"],
                "quantity": quantity,
                "line_total": round(line_total, 2),
            }
        )

    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO orders (customer_name, email, items_json, total, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (customer_name, email, json.dumps(normalized_items), round(order_total, 2), created_at),
        )
        connection.commit()

    return jsonify(
        service=SERVICE_NAME,
        order_id=cursor.lastrowid,
        customer_name=customer_name,
        email=email,
        items=normalized_items,
        total=round(order_total, 2),
        created_at=created_at,
    ), 201


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
