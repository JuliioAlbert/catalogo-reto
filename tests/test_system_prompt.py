"""The first message the model receives is a Spanish system prompt."""

import json

import pytest
from conftest import PRODUCT_DIR, ScriptedModel, final_answer

HISTORY = [
    {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
    for i in range(10)
]
REQUIRED_WORDS = (
    "answer",
    "tool",
    "get_product",
    "search_by_category",
    "product_id",
)


def first_call(make_client, history=None, **env):
    """Ask one question and return the messages sent to the model."""
    model = ScriptedModel(final_answer("ok"))
    client = make_client(model=model, **env)
    body = {"question": "Hola", "history": history or []}
    assert client.post("/ask", json=body).status_code == 200
    return model.calls[0]


def test_first_message_is_a_system_prompt_naming_the_protocol(make_client):
    system = first_call(make_client)[0]
    assert system["role"] == "system"
    for word in REQUIRED_WORDS:
        assert word in system["content"]
    assert "JSON" in system["content"]


def test_system_prompt_is_written_in_spanish(make_client):
    content = first_call(make_client)[0]["content"].casefold()
    assert any(word in content for word in ("responde", "herramienta", "solo"))


def test_system_prompt_contains_no_product_data(make_client):
    content = first_call(make_client)[0]["content"]
    products = json.loads((PRODUCT_DIR / "data" / "products.json").read_text("utf-8"))
    for product in products:
        assert product["name"] not in content


def test_window_of_one_keeps_the_system_prompt(make_client):
    sent = first_call(make_client, HISTORY, HISTORY_WINDOW=1)
    assert [m["role"] for m in sent] == ["system", "assistant", "user"]
    assert sent[1]["content"] == "msg 9"


def test_system_prompt_does_not_count_against_the_window(make_client):
    sent = first_call(make_client, HISTORY, HISTORY_WINDOW=2)
    assert [m["content"] for m in sent[1:]] == ["msg 8", "msg 9", "Hola"]
    assert len([m for m in sent if m["role"] == "system"]) == 1


@pytest.mark.parametrize("window", [50, 100])
def test_large_windows_also_keep_the_system_prompt(make_client, window):
    sent = first_call(make_client, HISTORY, HISTORY_WINDOW=window)
    assert sent[0]["role"] == "system"
    assert len(sent) == 1 + len(HISTORY) + 1
