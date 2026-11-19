"""API tests for the cost levers: window, cost, metrics, events and secrets."""

import json

import httpx
import pytest
from conftest import ALICE_KEY, ScriptedModel, final_answer, settings_for
from fastapi.testclient import TestClient

from app.config import load_config
from app.gateway import GatewayModel
from app.main import create_app

QUESTION = "Who is PRD-0001?"
SECRET = "cf-secret-token-xyz"


def test_only_the_last_history_messages_reach_the_model(make_client):
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(10)
    ]
    model = ScriptedModel(final_answer("ok"))
    client = make_client(model=model, HISTORY_WINDOW=2)
    reply = client.post("/ask", json={"question": "Hola", "history": history})
    assert reply.status_code == 200
    sent = model.calls[0]
    assert sent[0]["role"] == "system"
    assert [m["content"] for m in sent[1:]] == ["msg 8", "msg 9", "Hola"]


def test_levers_make_the_same_question_cheaper_and_metrics_add_it_up(make_client):
    cheap = make_client()
    baseline = make_client(ROUTING="false")
    cheap_cost = cheap.post("/ask", json={"question": QUESTION}).json()["cost_usd"]
    second = cheap.post("/ask", json={"question": QUESTION}).json()["cost_usd"]
    base_cost = baseline.post("/ask", json={"question": QUESTION}).json()["cost_usd"]
    assert 0 < cheap_cost < base_cost
    assert cheap.get("/metrics").json()["cost_usd"] == pytest.approx(
        cheap_cost + second
    )


def test_agent_run_event_has_cost_fields_and_never_the_text(make_logged_app):
    app = make_logged_app()
    app.client.post("/ask", json={"question": QUESTION})
    event = app.events("agent_run")[0]
    assert event["model"]
    assert event["route"]
    assert event["cached_calls"] == 0
    assert event["cost_usd"] > 0
    assert "PRD-0001" not in json.dumps(event)


def test_cloudflare_token_never_reaches_the_log_or_the_responses(catalog, capsys):
    env = {
        "MODEL_PROVIDER": "gateway",
        "CF_ACCOUNT_ID": "account",
        "CF_GATEWAY_ID": "gateway",
        "CF_API_TOKEN": SECRET,
    }
    config = load_config(settings_for(env))
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text=SECRET))
    model = GatewayModel(config, client=httpx.Client(transport=transport))
    client = TestClient(
        create_app(config=config, model=model, catalog=catalog),
        raise_server_exceptions=False,
        headers={"X-API-Key": ALICE_KEY},
    )
    responses = [
        client.post("/ask", json={"question": QUESTION}),
        client.get("/metrics"),
        client.get("/health"),
    ]
    assert responses[0].status_code == 502
    assert all(SECRET not in response.text for response in responses)
    assert SECRET not in capsys.readouterr().out
