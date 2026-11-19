"""Steps for the scenarios in features/hardening.feature."""

import json

import pytest
from conftest import ALICE_KEY, ScriptedModel, final_answer, settings_for
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.config import load_config
from app.main import create_app
from app.output import SAFE_ANSWER

scenarios("features/hardening.feature")


@pytest.fixture(name="state")
def state_fixture():
    """Options chosen by the Given steps and the last response."""
    return {"env": {}, "model": ScriptedModel(final_answer("listo"))}


@given(parsers.parse('PII mode is "{mode}"'))
def pii_mode(state, mode):
    state["env"]["PII_MODE"] = mode


@given(parsers.parse("the model answers with {size:d} characters, limit {n:d}"))
def long_answer(state, size, n):
    state["model"] = ScriptedModel(final_answer("x" * size))
    state["env"]["MAX_ANSWER_CHARS"] = n


@when(parsers.parse('I ask "{question}"'))
def ask(state, catalog, question, capsys):
    config = load_config(settings_for(state["env"]))
    app = create_app(config=config, model=state["model"], catalog=catalog)
    client = TestClient(app, headers={"X-API-Key": ALICE_KEY})
    state["response"] = client.post("/ask", json={"question": question})
    state["log"] = capsys.readouterr().out


@then(parsers.parse('the model never receives "{text}"'))
def model_never_receives(state, text):
    assert text not in json.dumps(state["model"].calls, ensure_ascii=False)


@then("the log has a pii_detected audit event without the value")
def log_has_event(state):
    out = state["log"]
    assert "pii_detected" in out
    assert "ana@example.com" not in out


@then(parsers.parse("the response status is {status:d}"))
def status_is(state, status):
    assert state["response"].status_code == status


@then(parsers.parse('the response detail is "{detail}"'))
def detail_is(state, detail):
    assert state["response"].json()["detail"] == detail


@then("the answer is the safe answer")
def answer_is_safe(state):
    assert state["response"].json()["answer"] == SAFE_ANSWER
