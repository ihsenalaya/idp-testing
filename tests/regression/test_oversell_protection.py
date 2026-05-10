"""
Regression: oversell protection.

Scenario: A product has a known stock level. Ordering more than available stock
must return 409 Conflict. After a valid order, the stock is decremented.
Ordering the exact remaining quantity must succeed; ordering one more must fail.

detectedImpacts: backend, orders
"""
import pytest

pytestmark = pytest.mark.requires_db


def test_order_refused_when_stock_insufficient(client):
    """409 when quantity exceeds available stock."""
    prod = client.post("/api/products", json={
        "name": "Limited Edition Widget", "price": 49.99, "stock": 3
    }).get_json()
    pid = prod["id"]

    r = client.post("/api/orders", json={"product_id": pid, "quantity": 5})
    assert r.status_code == 409
    assert "insufficient stock" in r.get_json()["error"]


def test_stock_decremented_after_valid_order(client):
    """Stock drops by exactly the ordered quantity."""
    prod = client.post("/api/products", json={
        "name": "Trackable Widget", "price": 29.99, "stock": 10
    }).get_json()
    pid = prod["id"]

    client.post("/api/orders", json={"product_id": pid, "quantity": 3})

    detail = client.get(f"/api/products/{pid}").get_json()
    assert detail["stock"] == 7


def test_order_exact_stock_succeeds(client):
    """Ordering the exact available stock should succeed."""
    prod = client.post("/api/products", json={
        "name": "Last-unit Widget", "price": 9.99, "stock": 2
    }).get_json()
    pid = prod["id"]

    r = client.post("/api/orders", json={"product_id": pid, "quantity": 2})
    assert r.status_code == 201


def test_zero_quantity_rejected(client):
    """Ordering quantity 0 must return 400."""
    prod = client.post("/api/products", json={
        "name": "Zero Qty Widget", "price": 5.00, "stock": 10
    }).get_json()

    r = client.post("/api/orders", json={"product_id": prod["id"], "quantity": 0})
    assert r.status_code == 400
