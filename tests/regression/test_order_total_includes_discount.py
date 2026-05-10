"""
[KAGENT DEMO] Regression: order response must include pre-computed total_price.

Scenario: When a product has a discount_pct, placing an order should return a
`total_price` field in the response that equals the discounted unit price ×
quantity. This makes the front-end cart summary straightforward to implement.

STATUS: INTENTIONALLY FAILING
Reason: The current POST /api/orders implementation does not return `total_price`.
Expected kagent analysis: "The order response is missing the `total_price` field.
Add it to the INSERT RETURNING clause in api_create_order() in app.py, computed
as ROUND(price * (1 - discount_pct/100) * quantity, 2)."

detectedImpacts: backend, api-contract, frontend
"""
import pytest

pytestmark = [pytest.mark.requires_db, pytest.mark.kagent_demo]


def test_order_response_includes_total_price(client):
    """POST /api/orders must return total_price = discounted_unit × quantity.

    INTENTIONAL FAILURE — demonstrates kagent AI analysis.
    Fix: add `total_price` to the order response in app.py::api_create_order().
    """
    prod = client.post("/api/products", json={
        "name": "Discounted Order Widget",
        "price": 100.00,
        "stock": 10,
        "discount_pct": 20.0,
    }).get_json()

    r = client.post("/api/orders", json={
        "product_id": prod["id"], "quantity": 3
    })
    assert r.status_code == 201
    order = r.get_json()

    # Expect total_price = 100 * 0.8 * 3 = 240.00
    # FAILS: current API does not return this field
    assert "total_price" in order, (
        "KAGENT DEMO FAILURE: order response missing `total_price` field. "
        "POST /api/orders returns: " + str(list(order.keys()))
    )
    assert order["total_price"] == 240.00


def test_order_total_price_no_discount(client):
    """Without a discount total_price must equal price × quantity.

    INTENTIONAL FAILURE — demonstrates kagent AI analysis.
    """
    prod = client.post("/api/products", json={
        "name": "Full Price Order Widget",
        "price": 25.00,
        "stock": 20,
        "discount_pct": 0.0,
    }).get_json()

    r = client.post("/api/orders", json={"product_id": prod["id"], "quantity": 4})
    assert r.status_code == 201
    order = r.get_json()

    assert "total_price" in order, (
        "KAGENT DEMO FAILURE: missing `total_price`"
    )
    assert order["total_price"] == 100.00
