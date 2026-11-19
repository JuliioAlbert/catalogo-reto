"""Unit tests for the fake model in app.llm."""

import json

import pytest

from app.llm import FakeModel


@pytest.fixture(name="model")
def model_fixture(catalog):
    return FakeModel(catalog)


def ask(model, text):
    """Send one user message and decode the JSON reply."""
    reply = model.complete([{"role": "user", "content": text}])
    return json.loads(reply) if isinstance(reply, str) else reply


def test_product_id_requests_get_product(model):
    assert ask(model, "Dime de PRD-0002") == {
        "tool": "get_product",
        "args": {"product_id": "PRD-0002"},
    }


def test_known_department_requests_department_search(model):
    reply = ask(model, "¿Qué hay en Oficina?")
    assert reply["tool"] == "search_by_category"


def test_tool_result_message_takes_priority_and_gets_an_answer(model):
    text = "Resultado de la herramienta: PRD-0001 Laptop Pro 14"
    reply = ask(model, text)
    assert reply == {"answer": f"Según el catálogo: {text.split(': ', 1)[1]}"}
