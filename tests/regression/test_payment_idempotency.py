"""
[KAGENT DEMO] Regression: duplicate payments must be rejected (idempotency).

Scenario: Sending the same payment request twice for the same order_id should
return 409 Conflict on the second attempt. This prevents double-charging and
is a critical safety invariant for any payment system.

STATUS: INTENTIONALLY FAILING
Reason: The current POST /api/payments implementation inserts a new payment row
on every call without checking for an existing completed payment on the same
order. It will return 201 twice instead of 409 on the second call.

Expected kagent analysis: "The payments endpoint is not idempotent. Add a check
in api_create_payment() in app.py: query for an existing payment with
`order_id = %s AND status = 'completed'` and return 409 if found."

detectedImpacts: backend, payments
"""
import pytest

pytestmark = [pytest.mark.requires_db, pytest.mark.kagent_demo]


@pytest.fixture
def paid_order(client):
    prod = client.post("/api/products", json={
        "name": "Idempotency Test Widget", "price": 50.00, "stock": 5
    }).get_json()
    order = client.post("/api/orders", json={
        "product_id": prod["id"], "quantity": 1
    }).get_json()
    return order


def test_second_payment_for_same_order_returns_409(client, paid_order):
    """Submitting payment twice for the same order must yield 409 on the second.

    INTENTIONAL FAILURE — demonstrates kagent AI analysis.
    Fix: in app.py::api_create_payment(), check for existing completed payment
    before inserting and return 409 if found.
    """
    payload = {"order_id": paid_order["id"], "amount": 50.00, "method": "card"}

    first = client.post("/api/payments", json=payload)
    assert first.status_code == 201, f"First payment should succeed, got {first.status_code}"

    # INTENTIONAL FAILURE: second call returns 201 instead of 409
    second = client.post("/api/payments", json=payload)
    assert second.status_code == 409, (
        "KAGENT DEMO FAILURE: duplicate payment was accepted (got "
        f"{second.status_code}). The payments endpoint must reject duplicate "
        "payments with HTTP 409."
    )


def test_payment_list_shows_single_payment_after_duplicate(client, paid_order):
    """Even after a duplicate submission, only one payment row must exist.

    INTENTIONAL FAILURE — demonstrates kagent AI analysis.
    """
    payload = {"order_id": paid_order["id"], "amount": 50.00, "method": "card"}
    client.post("/api/payments", json=payload)
    client.post("/api/payments", json=payload)  # duplicate

    payments = client.get("/api/payments").get_json()
    order_payments = [p for p in payments if p["order_id"] == paid_order["id"]]
    assert len(order_payments) == 1, (
        "KAGENT DEMO FAILURE: found " + str(len(order_payments)) +
        " payments for the same order — idempotency not enforced."
    )
