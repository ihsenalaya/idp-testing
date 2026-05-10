"""Shared pytest fixtures for all test categories."""
import os
import pathlib
import sys

import pytest

# Make sure the project root is importable
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATABASE_URL = os.environ.get("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", ""))
APP_URL = os.environ.get("APP_URL", "")


# ── Database fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_url():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL not set — skipping DB-backed tests")
    return DATABASE_URL


@pytest.fixture
def db(db_url):
    """Raw psycopg2 connection, rolled back after each test."""
    import psycopg2
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_cursor(db):
    cur = db.cursor()
    yield cur
    cur.close()


# ── Flask test-client fixtures ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def flask_app(db_url):
    """Return a Flask test app connected to the test database."""
    os.environ["DATABASE_URL"] = db_url
    import importlib
    import app as app_module
    importlib.reload(app_module)   # re-read DATABASE_URL after env patch
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    return app_module.app


@pytest.fixture
def client(flask_app):
    """Flask test client — each test gets a fresh request context."""
    with flask_app.test_client() as c:
        yield c


# ── Live API fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def api_base():
    if not APP_URL:
        pytest.skip("APP_URL not set — skipping live-API tests")
    return APP_URL.rstrip("/")


# ── Seed helpers ──────────────────────────────────────────────────────────────

@pytest.fixture
def seeded_product(client):
    """Insert a known product and return its id; cleaned up via rollback."""
    r = client.post("/api/products", json={
        "name": "Test Widget",
        "price": 100.00,
        "stock": 50,
        "discount_pct": 20.0,
    })
    assert r.status_code == 201
    return r.get_json()
