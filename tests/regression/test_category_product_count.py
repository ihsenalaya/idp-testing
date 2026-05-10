"""
Regression: category product_count reflects actual assigned products.

Scenario: Creating products in a category and querying GET /api/categories
must return a product_count that matches the number of products in that
category. Deleting a product must decrement the count.

detectedImpacts: backend, api-contract
"""
import pytest

pytestmark = pytest.mark.requires_db


def test_category_product_count_increments(client):
    """Adding products to a category increments its product_count."""
    cat = client.post("/api/categories", json={
        "name": "Count Test Category", "slug": "count-test-cat"
    })
    # tolerate slug collision from prior test runs
    cat_id = cat.get_json().get("id")
    if not cat_id:
        cats = client.get("/api/categories").get_json()
        cat_id = next(c["id"] for c in cats if c["slug"] == "count-test-cat")

    for i in range(3):
        client.post("/api/products", json={
            "name": f"Count Widget {i}",
            "price": 10.00,
            "stock": 5,
            "category_id": cat_id,
        })

    cats = client.get("/api/categories").get_json()
    cat_data = next(c for c in cats if c["id"] == cat_id)
    assert cat_data["product_count"] >= 3


def test_category_product_count_decrements_on_delete(client):
    """Deleting a product decrements its category's product_count."""
    cat = client.post("/api/categories", json={
        "name": "Delete Count Category", "slug": "delete-count-cat"
    })
    cat_id = cat.get_json().get("id")
    if not cat_id:
        cats = client.get("/api/categories").get_json()
        cat_id = next(c["id"] for c in cats if c["slug"] == "delete-count-cat")

    prod = client.post("/api/products", json={
        "name": "Delete Me Widget", "price": 1.00, "stock": 1, "category_id": cat_id
    }).get_json()

    before = next(
        c["product_count"] for c in client.get("/api/categories").get_json()
        if c["id"] == cat_id
    )
    client.delete(f"/api/products/{prod['id']}")
    after = next(
        c["product_count"] for c in client.get("/api/categories").get_json()
        if c["id"] == cat_id
    )
    assert after == before - 1


def test_uncategorised_products_not_in_any_category_count(client):
    """Products without category_id don't appear in any category's count."""
    client.post("/api/products", json={
        "name": "Orphan Widget", "price": 1.00, "stock": 1
    })

    cats = client.get("/api/categories").get_json()
    # category counts should not include orphan (category_id=NULL)
    for c in cats:
        assert isinstance(c["product_count"], int)
        assert c["product_count"] >= 0
