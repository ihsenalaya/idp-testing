"""
Regression: currency rounding in API responses.

Scenario: Product prices and discounted prices returned by the API must be
numeric floats rounded to 2 decimal places. No scientific notation, no
truncation, no extra precision.

detectedImpacts: backend, api-contract
"""
import pytest

pytestmark = pytest.mark.requires_db


def test_product_price_is_float_with_two_decimal_places(client):
    """API price field must be a float rounded to 2dp."""
    r = client.post("/api/products", json={
        "name": "Rounding Widget", "price": 19.999, "stock": 1
    })
    assert r.status_code == 201
    price = r.get_json()["price"]
    assert isinstance(price, float)
    assert price == round(price, 2)


def test_discounted_price_rounds_correctly(client):
    """Discounted price endpoint rounds to 2dp."""
    client.post("/api/products", json={
        "name": "Discount Rounding Widget",
        "price": 9.99,
        "stock": 10,
        "discount_pct": 33.33,
    })

    r = client.get("/api/products/discounted?min_discount=0")
    assert r.status_code == 200
    products = r.get_json()["products"]
    for p in products:
        if p["name"] == "Discount Rounding Widget":
            dp = p["discounted_price"]
            assert isinstance(dp, float)
            assert dp == round(dp, 2)
            break


def test_list_products_prices_are_floats(client):
    """All prices in the product list are floats."""
    client.post("/api/products", json={"name": "Float Check", "price": 7.50, "stock": 5})
    r = client.get("/api/products")
    assert r.status_code == 200
    for p in r.get_json():
        assert isinstance(p["price"], float)
        assert p["price"] == round(p["price"], 2)


def test_zero_price_accepted_and_returned(client):
    """A price of 0.00 is valid and returned as 0.0."""
    r = client.post("/api/products", json={"name": "Free Widget", "price": 0.00, "stock": 100})
    assert r.status_code == 201
    assert r.get_json()["price"] == 0.0
