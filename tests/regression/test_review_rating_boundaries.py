"""
Regression: review rating boundary validation.

Scenario: The /api/products/{id}/reviews endpoint must enforce that ratings
are integers between 1 and 5 inclusive. Values outside this range must return
400. Valid ratings must persist and be returned in subsequent GET requests.

detectedImpacts: backend, api-contract
"""
import pytest

pytestmark = pytest.mark.requires_db


@pytest.fixture
def product(client):
    r = client.post("/api/products", json={
        "name": "Reviewed Widget", "price": 29.99, "stock": 5
    })
    return r.get_json()


def test_rating_1_accepted(client, product):
    r = client.post(f"/api/products/{product['id']}/reviews",
                    json={"author": "tester", "rating": 1})
    assert r.status_code == 201
    assert r.get_json()["rating"] == 1


def test_rating_5_accepted(client, product):
    r = client.post(f"/api/products/{product['id']}/reviews",
                    json={"author": "tester", "rating": 5})
    assert r.status_code == 201
    assert r.get_json()["rating"] == 5


def test_rating_0_rejected(client, product):
    r = client.post(f"/api/products/{product['id']}/reviews",
                    json={"rating": 0})
    assert r.status_code == 400


def test_rating_6_rejected(client, product):
    r = client.post(f"/api/products/{product['id']}/reviews",
                    json={"rating": 6})
    assert r.status_code == 400


def test_rating_negative_rejected(client, product):
    r = client.post(f"/api/products/{product['id']}/reviews",
                    json={"rating": -1})
    assert r.status_code == 400


def test_review_persists_in_product_detail(client, product):
    """A submitted review appears in GET /api/products/{id}."""
    client.post(f"/api/products/{product['id']}/reviews",
                json={"author": "bob", "rating": 4, "comment": "Good widget"})
    detail = client.get(f"/api/products/{product['id']}").get_json()
    reviews = detail.get("reviews", [])
    assert any(r["author"] == "bob" and r["rating"] == 4 for r in reviews)


def test_anonymous_author_default(client, product):
    """Omitting author defaults to 'anonymous'."""
    r = client.post(f"/api/products/{product['id']}/reviews",
                    json={"rating": 3})
    assert r.status_code == 201
    assert r.get_json()["author"] == "anonymous"
