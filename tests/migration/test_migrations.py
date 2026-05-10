"""
Migration tests: verify each Alembic revision applies and reverts cleanly.

These tests run `alembic upgrade` and `alembic downgrade` against a live
PostgreSQL database, then query information_schema to assert the expected
table / column changes occurred.

Requires: DATABASE_URL env var pointing to a PostgreSQL instance.
"""
import os
import subprocess
import pathlib
import pytest
import psycopg2

pytestmark = pytest.mark.requires_db

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATABASE_URL = os.environ.get("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", ""))


def _alembic(args: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DATABASE_URL"] = DATABASE_URL
    return subprocess.run(
        ["python3", "-m", "alembic", *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _table_exists(conn, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=%s",
        (table,),
    )
    result = cur.fetchone() is not None
    cur.close()
    return result


def _column_exists(conn, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s AND column_name=%s",
        (table, column),
    )
    result = cur.fetchone() is not None
    cur.close()
    return result


@pytest.fixture(scope="module")
def conn():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL not set")
    c = psycopg2.connect(DATABASE_URL)
    c.autocommit = True
    yield c
    c.close()


# ── Migration 001: base schema ────────────────────────────────────────────────

class TestMigration001:
    def test_upgrade_creates_base_tables(self, conn):
        result = _alembic(["upgrade", "001"])
        assert result.returncode == 0, f"alembic upgrade 001 failed:\n{result.stderr}"
        for table in ("categories", "products", "reviews", "orders"):
            assert _table_exists(conn, table), f"table {table} missing after 001 upgrade"

    def test_downgrade_drops_base_tables(self, conn):
        result = _alembic(["downgrade", "base"])
        assert result.returncode == 0, f"alembic downgrade base failed:\n{result.stderr}"
        for table in ("categories", "products", "reviews", "orders"):
            assert not _table_exists(conn, table), f"table {table} still present after downgrade"

    def test_upgrade_again_idempotent(self, conn):
        result = _alembic(["upgrade", "001"])
        assert result.returncode == 0


# ── Migration 002: payments table ─────────────────────────────────────────────

class TestMigration002:
    def test_upgrade_creates_payments_table(self, conn):
        _alembic(["upgrade", "001"])  # ensure prerequisite
        result = _alembic(["upgrade", "002"])
        assert result.returncode == 0, f"alembic upgrade 002 failed:\n{result.stderr}"
        assert _table_exists(conn, "payments"), "payments table missing after 002 upgrade"

    def test_payments_has_required_columns(self, conn):
        for col in ("id", "order_id", "amount", "method", "transaction_id", "status", "created_at"):
            assert _column_exists(conn, "payments", col), f"payments.{col} missing"

    def test_downgrade_drops_payments_table(self, conn):
        result = _alembic(["downgrade", "001"])
        assert result.returncode == 0, f"alembic downgrade 001 failed:\n{result.stderr}"
        assert not _table_exists(conn, "payments"), "payments still present after downgrade"


# ── Migration 003: discount_code column ──────────────────────────────────────

class TestMigration003:
    def test_upgrade_adds_discount_code_column(self, conn):
        _alembic(["upgrade", "002"])  # ensure prerequisite
        result = _alembic(["upgrade", "003"])
        assert result.returncode == 0, f"alembic upgrade 003 failed:\n{result.stderr}"
        assert _column_exists(conn, "orders", "discount_code"), \
            "orders.discount_code missing after 003 upgrade"

    def test_discount_code_column_is_nullable(self, conn):
        cur = conn.cursor()
        cur.execute(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='orders' AND column_name='discount_code'"
        )
        row = cur.fetchone()
        cur.close()
        assert row is not None
        assert row[0] == "YES", "orders.discount_code must be nullable"

    def test_downgrade_removes_discount_code_column(self, conn):
        result = _alembic(["downgrade", "002"])
        assert result.returncode == 0, f"alembic downgrade 002 failed:\n{result.stderr}"
        assert not _column_exists(conn, "orders", "discount_code"), \
            "discount_code still present after downgrade"

    def test_full_up_down_cycle(self, conn):
        """Full upgrade head → downgrade base round-trip completes without error."""
        r1 = _alembic(["upgrade", "head"])
        assert r1.returncode == 0, r1.stderr
        r2 = _alembic(["downgrade", "base"])
        assert r2.returncode == 0, r2.stderr
