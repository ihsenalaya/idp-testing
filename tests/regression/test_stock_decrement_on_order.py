"""
Regression: stock is decremented atomically when an order is placed.

Scenario: Place multiple sequential orders on the same product; the stock
reported by GET /api/products/{id} must decrease by exactly the ordered
quantity after each order, and must never go negative.

detectedImpacts: backend, orders
"""
import pytest

pytestmark = pytest.mark.requires_db


def test_sequential_orders_decrement_stock(client):
    """Three sequential orders of qty 2 reduce stock from 10 to 4."""
    prod = client.post("/api/products", json={
        "name": "Sequential Stock Widget", "price": 15.00, "stock": 10
    }).get_json()
    pid = prod["id"]

    for _ in range(3):
        r = client.post("/api/orders", json={"product_id": pid, "quantity": 2})
        assert r.status_code == 201

    detail = client.get(f"/api/products/{pid}").get_json()
    assert detail["stock"] == 4


def test_stock_never_goes_negative(client):
    """Ordering more than available stock is refused, stock unchanged."""
    prod = client.post("/api/products", json={
        "name": "Neg Stock Guard Widget", "price": 10.00, "stock": 3
    }).get_json()
    pid = prod["id"]

    # Drain to 1
    client.post("/api/orders", json={"product_id": pid, "quantity": 2})

    # Try to order 5 more (only 1 left)
    r = client.post("/api/orders", json={"product_id": pid, "quantity": 5})
    assert r.status_code == 409

    # Confirm stock is still 1
    detail = client.get(f"/api/products/{pid}").get_json()
    assert detail["stock"] == 1


def test_order_list_reflects_all_orders(client):
    """Every placed order appears in GET /api/orders."""
    prod = client.post("/api/products", json={
        "name": "Order List Widget", "price": 5.00, "stock": 20
    }).get_json()

    ids = []
    for i in range(3):
        r = client.post("/api/orders", json={"product_id": prod["id"], "quantity": 1})
        ids.append(r.get_json()["id"])

    orders = client.get("/api/orders").get_json()
    existing_ids = {o["id"] for o in orders}
    for oid in ids:
        assert oid in existing_ids
