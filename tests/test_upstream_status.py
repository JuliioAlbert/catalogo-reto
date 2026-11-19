"""The error event reports the gateway HTTP status, and never any secret."""

import json

import httpx
import pytest
from conftest import ALICE_KEY, WALL_TIME, TickingClock, settings_for
from fastapi.testclient import TestClient

from app.config import load_config
from app.gateway import GatewayModel
from app.main import create_app

QUESTION = "Who is PRD-0001?"
TOKEN = "tok-upstream-secret"
BODY_TEXT = "upstream-body-secret"


def _raise_timeout(request):
    raise httpx.ReadTimeout("timeout-detail-secret", request=request)


def gateway_app(catalog, capsys, handler):
    """Build an app whose gateway model talks to a mock transport."""
    config = load_config(
        settings_for(
            {
                "MODEL_PROVIDER": "gateway",
                "CF_ACCOUNT_ID": "acc",
                "CF_GATEWAY_ID": "gw",
                "CF_API_TOKEN": TOKEN,
            }
        )
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    app = create_app(
        config=config,
        model=GatewayModel(config, client=client),
        catalog=catalog,
        clock=TickingClock(),
        wall_clock=lambda: WALL_TIME,
    )
    http = TestClient(
        app, raise_server_exceptions=False, headers={"X-API-Key": ALICE_KEY}
    )
    response = http.post("/ask", json={"question": QUESTION})
    lines = capsys.readouterr().out.splitlines()
    events = [json.loads(line) for line in lines if line]
    return response, [e for e in events if e["event"] == "error"], lines


@pytest.mark.parametrize("status", [401, 404])
def test_error_event_carries_the_gateway_status_code(catalog, capsys, status):
    response, errors, _ = gateway_app(
        catalog, capsys, lambda request: httpx.Response(status, text=BODY_TEXT)
    )
    assert response.status_code == 502
    assert len(errors) == 1
    assert errors[0]["upstream_status"] == status


@pytest.mark.parametrize(
    "handler",
    [_raise_timeout, lambda request: httpx.Response(200, text="not json")],
    ids=["timeout", "malformed-json"],
)
def test_failures_without_an_http_error_have_no_status_code(
    catalog, capsys, handler
):
    response, errors, _ = gateway_app(catalog, capsys, handler)
    assert response.status_code == 502
    assert len(errors) == 1
    assert errors[0].get("upstream_status") is None


def test_token_body_and_error_message_never_reach_the_log_or_the_502(
    catalog, capsys
):
    response, _, lines = gateway_app(
        catalog, capsys, lambda request: httpx.Response(401, text=BODY_TEXT)
    )
    everything = response.text + "\n".join(lines)
    assert response.json()["detail"] == "model unavailable"
    assert TOKEN not in everything
    assert BODY_TEXT not in everything
    assert "Client error" not in everything
