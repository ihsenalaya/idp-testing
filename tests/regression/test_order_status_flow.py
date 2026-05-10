"""
Regression: order status lifecycle.

Scenario: A newly placed order has status 'pending'. After a payment is
processed via POST /api/payments, the order status must transition to 'paid'.
The orders list must reflect the updated status.

detectedImpacts: backend, payments, orders
"""
import pytest

pytestmark = pytest.mark.requires_db


@pytest.fixture
def product_with_stock(client):
    r = client.post("/api/products", json={
        "name": "Payment Flow Widget", "price": 99.00, "stock": 10
    })
    return r.get_json()


def test_new_order_has_pending_status(client, product_with_stock):
    """Freshly placed order must have status='pending'."""
    r = client.post("/api/orders", json={
        "product_id": product_with_stock["id"], "quantity": 1
    })
    assert r.status_code == 201
    assert r.get_json()["status"] == "pending"


def test_payment_transitions_order_to_paid(client, product_with_stock):
    """POST /api/payments sets order status to 'paid'."""
    order = client.post("/api/orders", json={
        "product_id": product_with_stock["id"], "quantity": 1
    }).get_json()

    payment = client.post("/api/payments", json={
        "order_id": order["id"],
        "amount": 99.00,
        "method": "card",
    })
    assert payment.status_code == 201
    pay_data = payment.get_json()
    assert pay_data["status"] == "completed"
    assert pay_data["transaction_id"]

    orders = client.get("/api/orders").get_json()
    matched = next((o for o in orders if o["id"] == order["id"]), None)
    assert matched is not None
    assert matched["status"] == "paid"


def test_payment_for_nonexistent_order_returns_404(client):
    """Payment against a non-existent order_id must return 404."""
    r = client.post("/api/payments", json={
        "order_id": 999999, "amount": 50.00
    })
    assert r.status_code == 404


def test_payment_requires_amount(client, product_with_stock):
    """POST /api/payments without amount returns 400."""
    order = client.post("/api/orders", json={
        "product_id": product_with_stock["id"], "quantity": 1
    }).get_json()

    r = client.post("/api/payments", json={"order_id": order["id"]})
    assert r.status_code == 400
