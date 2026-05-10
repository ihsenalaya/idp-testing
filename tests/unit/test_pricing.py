"""
Unit tests for pure pricing functions in app.py.

These tests run without a database or running server.
They verify the core business logic: discount application,
order totals, VAT calculation, and stock validation.
"""
import pytest
from app import (
    calculate_discounted_price,
    calculate_order_total,
    apply_vat,
    validate_stock,
)


# ── calculate_discounted_price ─────────────────────────────────────────────────

def test_zero_discount_returns_original_price():
    assert calculate_discounted_price(100.00, 0) == 100.00


def test_ten_percent_discount():
    assert calculate_discounted_price(100.00, 10) == 90.00


def test_twenty_percent_discount():
    assert calculate_discounted_price(199.99, 20) == 159.99


def test_fifty_percent_discount():
    assert calculate_discounted_price(80.00, 50) == 40.00


def test_hundred_percent_discount_is_zero():
    assert calculate_discounted_price(59.99, 100) == 0.00


def test_discount_rounds_to_two_decimal_places():
    # 33.33% of 9.99 = 3.33, so 9.99 - 3.33 = 6.66
    result = calculate_discounted_price(9.99, 33.33)
    assert result == round(result, 2)
    assert isinstance(result, float)


def test_discount_below_zero_raises():
    with pytest.raises(ValueError, match="discount_pct must be 0"):
        calculate_discounted_price(100.00, -1)


def test_discount_above_100_raises():
    with pytest.raises(ValueError, match="discount_pct must be 0"):
        calculate_discounted_price(100.00, 101)


def test_large_price_precision():
    result = calculate_discounted_price(9999.99, 15)
    assert result == 8499.99


def test_small_price_with_discount():
    assert calculate_discounted_price(0.01, 50) == 0.01


# ── calculate_order_total ─────────────────────────────────────────────────────

def test_order_total_no_discount_single_unit():
    assert calculate_order_total(50.00, 0, 1) == 50.00


def test_order_total_no_discount_multi_unit():
    assert calculate_order_total(25.00, 0, 4) == 100.00


def test_order_total_with_discount_multi_unit():
    # 100.00 at 20% = 80.00 per unit × 3 = 240.00
    assert calculate_order_total(100.00, 20, 3) == 240.00


def test_order_total_fractional_result_rounded():
    result = calculate_order_total(9.99, 10, 3)
    assert result == round(result, 2)


def test_order_total_zero_quantity_raises():
    with pytest.raises(ValueError, match="quantity must be >= 1"):
        calculate_order_total(100.00, 0, 0)


def test_order_total_negative_quantity_raises():
    with pytest.raises(ValueError, match="quantity must be >= 1"):
        calculate_order_total(100.00, 0, -1)


# ── apply_vat ─────────────────────────────────────────────────────────────────

def test_vat_default_rate_twenty_percent():
    assert apply_vat(100.00) == 120.00


def test_vat_zero_rate():
    assert apply_vat(100.00, 0.0) == 100.00


def test_vat_custom_rate():
    assert apply_vat(200.00, 0.10) == 220.00


def test_vat_rounds_to_two_decimal_places():
    result = apply_vat(9.99)
    assert result == round(result, 2)


def test_vat_negative_rate_raises():
    with pytest.raises(ValueError, match="VAT rate must be >= 0"):
        apply_vat(100.00, -0.05)


# ── validate_stock ────────────────────────────────────────────────────────────

def test_stock_sufficient_exact_match():
    assert validate_stock(5, 5) is True


def test_stock_sufficient_with_surplus():
    assert validate_stock(10, 3) is True


def test_stock_insufficient():
    assert validate_stock(2, 5) is False


def test_stock_zero_available_any_request_fails():
    assert validate_stock(0, 1) is False


def test_stock_zero_requested_fails():
    assert validate_stock(100, 0) is False
