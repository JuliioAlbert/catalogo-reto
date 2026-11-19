"""Unit tests for app.catalog."""

import pytest

from app.catalog import Catalog


def test_existing_product_is_found(catalog):
    product = catalog.get_product("PRD-0004")
    assert product["name"] == "Audífonos Studio"


def test_unknown_product_is_reported_as_missing(catalog):
    assert catalog.get_product("PRD-9999") is None


def test_category_search_ignores_case_and_returns_everyone(catalog):
    names = {e["name"] for e in catalog.search_by_category("electrónica")}
    assert names == {"Laptop Pro 14", "Teléfono Básico", "Audífonos Studio"}


def test_category_without_products_returns_empty_list(catalog):
    assert not catalog.search_by_category("Marketing")


def test_missing_data_file_is_an_error(tmp_path):
    with pytest.raises((OSError, ValueError)):
        Catalog(tmp_path / "nope.json")
