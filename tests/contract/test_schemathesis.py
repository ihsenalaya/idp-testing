"""
Contract tests using schemathesis.

Schemathesis generates test cases from the OpenAPI spec at api/openapi.yaml
and validates every response against the declared schema. These tests catch
contract drift — when the implementation diverges from the spec.

Run against a live API server:
    APP_URL=http://localhost:8080 python3 -m pytest tests/contract/ -v

Requires: schemathesis, APP_URL env var pointing to a running API.
"""
import os
import pathlib
import pytest

try:
    import schemathesis
    from schemathesis.specs.openapi import loaders as openapi_loaders
    SCHEMATHESIS_AVAILABLE = True
except ImportError:
    SCHEMATHESIS_AVAILABLE = False

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "api" / "openapi.yaml"
APP_URL = os.environ.get("APP_URL", "")

pytestmark = pytest.mark.requires_api

if not APP_URL:
    pytest.skip("APP_URL not set — skipping contract tests", allow_module_level=True)

if not SCHEMATHESIS_AVAILABLE:
    pytest.skip("schemathesis not installed — skipping contract tests", allow_module_level=True)


schema = schemathesis.from_path(
    str(SPEC_PATH),
    base_url=APP_URL,
    validate_schema=False,
)


@schema.parametrize()
def test_api_matches_openapi_spec(case):
    """Every endpoint defined in openapi.yaml must return a response that
    validates against the declared schema (status code + response body shape).

    A failure here means either:
    - The implementation returns a different shape than the spec declares, OR
    - The spec was updated but the implementation wasn't (or vice versa).
    """
    response = case.call()
    case.validate_response(response)


# ── Explicit smoke checks for critical paths ──────────────────────────────────

def test_healthz_returns_ok():
    """GET /healthz returns 200 with body 'ok'."""
    import requests
    r = requests.get(f"{APP_URL}/healthz", timeout=5)
    assert r.status_code == 200
    assert r.text.strip() == "ok"


def test_readyz_returns_ready():
    """GET /readyz returns 200 with body 'ready' when DB is reachable."""
    import requests
    r = requests.get(f"{APP_URL}/readyz", timeout=5)
    assert r.status_code in (200, 503)  # 503 if DB unavailable
    if r.status_code == 200:
        assert r.text.strip() == "ready"


def test_products_list_conforms_to_schema():
    """GET /api/products returns an array whose items have required fields."""
    import requests
    r = requests.get(f"{APP_URL}/api/products", timeout=5)
    assert r.status_code == 200
    products = r.json()
    assert isinstance(products, list)
    for p in products:
        assert "id" in p
        assert "name" in p
        assert "price" in p
        assert isinstance(p["price"], (int, float))


def test_stats_conforms_to_schema():
    """GET /api/stats returns object with all required keys."""
    import requests
    r = requests.get(f"{APP_URL}/api/stats", timeout=5)
    assert r.status_code == 200
    data = r.json()
    required = [
        "total_products", "total_categories", "total_reviews",
        "total_orders", "out_of_stock", "low_stock", "categories",
    ]
    for key in required:
        assert key in data, f"stats response missing key: {key}"


def test_create_product_response_conforms():
    """POST /api/products 201 response has the declared shape."""
    import requests
    r = requests.post(f"{APP_URL}/api/products", json={
        "name": "Contract Test Widget", "price": 9.99, "stock": 1
    }, timeout=5)
    assert r.status_code == 201
    p = r.json()
    for field in ("id", "name", "price", "stock", "discount_pct", "created_at"):
        assert field in p, f"product create response missing field: {field}"
