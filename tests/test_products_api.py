"""Unit tests for GET /products."""

import pytest
from conftest import KEYS


def test_products_without_a_key_is_rejected(make_client):
    response = make_client(key=None).get("/products")
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or missing API key"


def test_products_lists_everything_with_categories(client):
    body = client.get("/products").json()
    assert len(body["products"]) == 12
    assert body["categories"] == ["Deportes", "Electrónica", "Hogar", "Oficina"]


@pytest.mark.parametrize(
    "query, count",
    [
        ("category=hogar", 3),
        ("status=descontinuado", 2),
        ("in_stock=true&category=Deportes", 2),
        ("category=Nada", 0),
    ],
)
def test_products_filters(client, query, count):
    assert len(client.get(f"/products?{query}").json()["products"]) == count


TOO_LONG = "x" * 51


@pytest.mark.parametrize(
    "query", ["status=roto", "in_stock=quizas", f"category={TOO_LONG}"]
)
def test_products_rejects_invalid_parameters(client, query):
    assert client.get(f"/products?{query}").status_code == 422


def test_products_shares_the_rate_limit(make_client):
    client = make_client(RATE_LIMIT_PER_MINUTE=2)
    codes = [client.get("/products").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_products_writes_an_audit_event_with_the_client(make_logged_app):
    app = make_logged_app()
    app.client.get("/products?category=Hogar")
    events = [e for e in app.events("audit") if e.get("action") == "list_products"]
    assert events[0]["client"] == "alice"
    assert events[0]["category"] == "Hogar"
    assert KEYS["alice"] not in str(events)
