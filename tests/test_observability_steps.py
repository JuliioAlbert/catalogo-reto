"""Steps for the scenarios in features/observability.feature."""

import uuid

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from conftest import BrokenModel

scenarios("features/observability.feature")


@pytest.fixture(name="options")
def options_fixture():
    """Keyword arguments for the app, chosen by the Given steps."""
    return {}


@pytest.fixture(name="outcome")
def outcome_fixture():
    """Holds the last HTTP response."""
    return {}


@pytest.fixture(name="app")
def app_fixture(make_logged_app, options):
    """The app under test, built after the Given steps have run."""
    return make_logged_app(**options)


@given("the model is broken")
def broken_model(options):
    options["model"] = BrokenModel()


@given("tracing is enabled without an API key")
def tracing_without_key(options, monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    options["LANGSMITH_TRACING"] = "true"


@when("I request the health check")
def request_health(app, outcome):
    outcome["response"] = app.client.get("/health")


@when(parsers.parse('I ask "{question}" with request id "{request_id}"'))
def ask_with_request_id(app, outcome, question, request_id):
    outcome["response"] = app.client.post(
        "/ask",
        json={"question": question},
        headers={"X-Request-ID": request_id},
    )


@when(parsers.parse('I ask "{question}" {count:d} times'))
def ask_many_times(app, question, count):
    for _ in range(count):
        app.client.post("/ask", json={"question": question})


@then("the response carries a generated request id")
def has_generated_request_id(outcome):
    assert uuid.UUID(outcome["response"].headers["X-Request-ID"])


@then(parsers.parse('the response header and body request id are "{request_id}"'))
def request_id_is_kept(outcome, request_id):
    response = outcome["response"]
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["request_id"] == request_id


@then(parsers.parse("the response status is {status:d}"))
def check_status(outcome, status):
    assert outcome["response"].status_code == status


@then(parsers.parse('the response body request id is "{request_id}"'))
def body_request_id(outcome, request_id):
    assert outcome["response"].json()["request_id"] == request_id


@then(parsers.parse('the log has an error event for request "{request_id}"'))
def log_has_error_event(app, request_id):
    errors = app.events("error")
    assert [e["request_id"] for e in errors] == [request_id]


@then(parsers.parse('the log has an agent run event for request "{request_id}"'))
def log_has_agent_run(app, request_id):
    runs = app.events("agent_run")
    assert [e["request_id"] for e in runs] == [request_id]


@then(parsers.parse('the log does not contain "{text}"'))
def log_does_not_contain(app, text):
    assert text not in str(app.events())


@then(parsers.parse("the metrics report at least {count:d} requests"))
def metrics_count_requests(app, count):
    assert app.client.get("/metrics").json()["requests"] >= count


@then("the metrics include an SLO verdict")
def metrics_have_slo(app):
    assert isinstance(app.client.get("/metrics").json()["slo"]["met"], bool)
