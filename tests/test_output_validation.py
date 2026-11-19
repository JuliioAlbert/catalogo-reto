"""Unit tests for app.output and the PII and output rules in /ask."""

import pytest
from conftest import ScriptedModel, final_answer, settings_for

from app.config import load_config
from app.output import SAFE_ANSWER, rejection_reason


@pytest.mark.parametrize(
    "answer, expected",
    [("Hola", None), ("", "empty"), ("   ", "empty"), ("x" * 11, "too_long"),
     (None, "not_text")],
)
def test_rejection_reason(answer, expected):
    assert rejection_reason(answer, 10) == expected


def test_pii_in_the_question_is_masked_before_reaching_the_model(make_client):
    model = ScriptedModel(final_answer("listo"))
    client = make_client(model=model)
    client.post("/ask", json={"question": "Mi correo es ana@example.com"})
    sent = " ".join(str(m["content"]) for m in model.calls[0])
    assert "ana@example.com" not in sent
    assert "[CORREO]" in sent


def test_pii_in_the_history_is_masked_too(make_client):
    model = ScriptedModel(final_answer("listo"))
    client = make_client(model=model)
    history = [{"role": "user", "content": "Llamame al 5512345678"}]
    client.post("/ask", json={"question": "Hola", "history": history})
    assert "5512345678" not in str(model.calls[0])


def test_block_mode_rejects_a_question_with_pii(make_client):
    model = ScriptedModel(final_answer("listo"))
    client = make_client(model=model, PII_MODE="block")
    response = client.post("/ask", json={"question": "RFC LOPA800101AB1"})
    assert response.status_code == 422
    assert response.json()["detail"] == "sensitive data detected"
    assert not model.calls


def test_pii_in_the_answer_is_masked(make_client):
    client = make_client(model=ScriptedModel(final_answer("Escribe a x@example.com")))
    body = client.post("/ask", json={"question": "Hola"}).json()
    assert "x@example.com" not in body["answer"]
    assert "[CORREO]" in body["answer"]


def test_block_mode_replaces_an_answer_with_pii(make_client):
    client = make_client(
        model=ScriptedModel(final_answer("Escribe a x@example.com")), PII_MODE="block"
    )
    answer = client.post("/ask", json={"question": "Hola"}).json()["answer"]
    assert answer == SAFE_ANSWER


def test_an_answer_over_the_limit_is_replaced(make_client):
    client = make_client(
        model=ScriptedModel(final_answer("x" * 50)), MAX_ANSWER_CHARS=10
    )
    answer = client.post("/ask", json={"question": "Hola"}).json()["answer"]
    assert answer == SAFE_ANSWER


def test_pii_audit_event_names_types_but_not_values(make_logged_app):
    app = make_logged_app()
    app.client.post("/ask", json={"question": "Mi correo es ana@example.com"})
    text = str(app.events("audit"))
    assert "pii_detected" in text and "email" in text
    assert "ana@example.com" not in text


def test_an_invalid_pii_mode_prevents_start():
    with pytest.raises(ValueError, match="PII_MODE"):
        load_config(settings_for({"PII_MODE": "maybe"}))
