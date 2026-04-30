import os
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

SERVICE_NAME = "gateway"
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:5000")


def forward(path, method="GET", payload=None):
    response = requests.request(
        method=method,
        url=f"{BACKEND_URL}{path}",
        json=payload,
        timeout=5,
    )
    return response


@app.get("/")
def home():
    return jsonify(
        service=SERVICE_NAME,
        message="Gateway is online and connected to the backend network.",
        routes=["/health", "/api/products", "/api/orders", "/api/summary"],
    )


@app.get("/health")
def health():
    backend_health = forward("/health")
    backend_health.raise_for_status()
    return jsonify(status="ok", service=SERVICE_NAME, backend=backend_health.json())


@app.get("/api/products")
def products():
    backend_response = forward("/api/products")
    backend_response.raise_for_status()
    return jsonify(backend_response.json())


@app.route("/api/orders", methods=["GET", "POST"])
def orders():
    if request.method == "GET":
        backend_response = forward("/api/orders")
    else:
        backend_response = forward("/api/orders", method="POST", payload=request.get_json(silent=True))

    backend_response.raise_for_status()
    return jsonify(backend_response.json()), backend_response.status_code


@app.get("/api/summary")
def summary():
    backend_response = forward("/api/summary")
    backend_response.raise_for_status()
    backend_payload = backend_response.json()

    return jsonify(
        service=SERVICE_NAME,
        message="Gateway successfully fetched store data from the protected backend.",
        backend=backend_payload,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
