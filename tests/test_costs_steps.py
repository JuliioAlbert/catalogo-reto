"""Steps for the scenarios in features/costs.feature."""

import httpx
import pytest
from conftest import ALICE_KEY, LARGE_MODEL, SMALL_MODEL, settings_for
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.config import load_config
from app.gateway import GatewayModel
from app.main import create_app

scenarios("features/costs.feature")


@pytest.fixture(name="settings")
def settings_fixture():
    """Environment overrides chosen by the Given steps."""
    return {}


@pytest.fixture(name="outcome")
def outcome_fixture():
    """Holds the last HTTP response."""
    return {}


@given("routing is disabled")
def routing_disabled(settings):
    settings["ROUTING"] = "false"


@given("the gateway is down")
def gateway_down(settings):
    settings.update(
        MODEL_PROVIDER="gateway",
        CF_ACCOUNT_ID="account",
        CF_GATEWAY_ID="gateway",
        CF_API_TOKEN="token-value",
    )


@when(parsers.parse('I ask "{question}"'))
def ask_question(make_client, catalog, settings, outcome, question):
    if settings.get("MODEL_PROVIDER") == "gateway":
        config = load_config(settings_for(settings))
        transport = httpx.MockTransport(lambda request: httpx.Response(500))
        model = GatewayModel(config, client=httpx.Client(transport=transport))
        app = create_app(config=config, model=model, catalog=catalog)
        client = TestClient(
            app, raise_server_exceptions=False, headers={"X-API-Key": ALICE_KEY}
        )
    else:
        client = make_client(**settings)
    outcome["response"] = client.post("/ask", json={"question": question})


@then(parsers.parse("the response status is {status:d}"))
def check_status(outcome, status):
    assert outcome["response"].status_code == status


@then("the model used is the small model")
def model_is_small(outcome):
    assert outcome["response"].json()["model"] == SMALL_MODEL


@then("the model used is the large model")
def model_is_large(outcome):
    assert outcome["response"].json()["model"] == LARGE_MODEL


@then("the route is reported")
def route_is_reported(outcome):
    route = outcome["response"].json()["route"]
    assert isinstance(route, str) and route


@then("the response reports a positive cost and no cached calls")
def cost_is_reported(outcome):
    body = outcome["response"].json()
    assert body["cost_usd"] > 0
    assert body["cached_calls"] == 0


@then(parsers.parse('the detail is "{text}"'))
def detail_is(outcome, text):
    assert outcome["response"].json()["detail"] == text


@then("the response carries a request id")
def has_request_id(outcome):
    body = outcome["response"].json()
    assert body["request_id"]
    assert outcome["response"].headers["X-Request-ID"] == body["request_id"]
