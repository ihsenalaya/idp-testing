"""
Regression: percent discount applied before VAT calculation.

Scenario: When a discounted price is displayed, the discount must be applied
to the base price first. The discounted_price field in /api/products/discounted
must equal price * (1 - discount_pct/100), rounded to 2dp.

This invariant ensures the frontend displays correct pre-tax prices and that
downstream tax calculations start from the correct base.

detectedImpacts: backend, api-contract
"""
import pytest
from app import calculate_discounted_price

pytestmark = pytest.mark.requires_db


def _discounted_price(price, pct):
    return round(price * (1 - pct / 100), 2)


def test_discounted_product_price_matches_formula(client):
    """API discounted_price must equal price*(1-pct/100)."""
    client.post("/api/products", json={
        "name": "Discount Formula Widget",
        "price": 100.00,
        "stock": 10,
        "discount_pct": 25.0,
    })

    r = client.get("/api/products/discounted?min_discount=0")
    products = r.get_json()["products"]
    widget = next((p for p in products if p["name"] == "Discount Formula Widget"), None)
    assert widget is not None
    expected = _discounted_price(widget["price"], widget["discount_pct"])
    assert widget["discounted_price"] == expected


def test_no_discount_discounted_price_equals_base(client):
    """A product with 0% discount has discounted_price == price."""
    client.post("/api/products", json={
        "name": "No Discount Widget",
        "price": 55.50,
        "stock": 5,
        "discount_pct": 0.0,
    })

    r = client.get("/api/products/discounted?min_discount=0")
    products = r.get_json()["products"]
    widget = next((p for p in products if p["name"] == "No Discount Widget"), None)
    if widget:
        assert widget["discounted_price"] == widget["price"]


def test_pure_discount_formula_matches_api_computation():
    """Unit-level: pure function must match the formula used by the API."""
    price, pct = 199.99, 15.0
    assert calculate_discounted_price(price, pct) == _discounted_price(price, pct)


def test_high_discount_boundary(client):
    """90% discount: discounted_price is 10% of base."""
    client.post("/api/products", json={
        "name": "90 Percent Off Widget",
        "price": 200.00,
        "stock": 1,
        "discount_pct": 90.0,
    })

    r = client.get("/api/products/discounted?min_discount=89")
    products = r.get_json()["products"]
    widget = next((p for p in products if p["name"] == "90 Percent Off Widget"), None)
    assert widget is not None
    assert widget["discounted_price"] == 20.00
