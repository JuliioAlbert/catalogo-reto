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


def test_list_products_without_filters_returns_everything(catalog):
    assert len(catalog.list_products()) == 12


def test_list_products_filters_by_category_ignoring_case(catalog):
    names = {p["name"] for p in catalog.list_products(category="oficina")}
    assert names == {"Silla Ergonómica", "Escritorio Elevable", "Lámpara de Escritorio"}


def test_list_products_filters_by_status_and_stock(catalog):
    discontinued = catalog.list_products(status="descontinuado")
    assert {p["id"] for p in discontinued} == {"PRD-0003", "PRD-0010"}
    assert all(p["stock"] > 0 for p in catalog.list_products(in_stock=True))
    assert all(p["stock"] == 0 for p in catalog.list_products(in_stock=False))


def test_list_products_combines_filters(catalog):
    found = catalog.list_products(category="Electrónica", status="activo")
    assert {p["id"] for p in found} == {"PRD-0001", "PRD-0004"}
