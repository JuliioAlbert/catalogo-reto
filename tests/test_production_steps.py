"""Steps for the scenarios in features/production.feature."""

import pytest
from conftest import KEYS, FakeClock, ScriptedModel, settings_for
from pytest_bdd import given, parsers, scenarios, then, when

from app.config import load_config
from app.main import create_app

scenarios("features/production.feature")

API_KEY_HEADER = "X-API-Key"
VALID_PRODUCTION = {
    "ENVIRONMENT": "production",
    "MODEL_PROVIDER": "gateway",
    "CF_ACCOUNT_ID": "account",
    "CF_API_TOKEN": "cloudflare-token",
    "API_KEYS": "alice:abcdefghijklmnop",
}


@pytest.fixture(name="options")
def options_fixture():
    """Keyword arguments for the app, chosen by the Given steps."""
    return {}


@pytest.fixture(name="outcome")
def outcome_fixture():
    """Holds the last HTTP response or the startup error."""
    return {}


@pytest.fixture(name="clock")
def clock_fixture():
    """A clock the scenarios move by hand."""
    return FakeClock()


@pytest.fixture(name="app")
def app_fixture(make_logged_app, options, clock):
    """The app under test, built after the Given steps have run."""
    return make_logged_app(clock=clock, **options)


def _ask(app, name, question="Who is PRD-0004?"):
    """Ask as the named client and return the response."""
    return app.client.post(
        "/ask", json={"question": question}, headers={API_KEY_HEADER: KEYS[name]}
    )


@given("no API key is sent")
def no_key(options):
    options["key"] = None


@given(parsers.parse('the API key "{key}" is sent'))
def wrong_key(options, key):
    options["key"] = key


@given(parsers.parse("the rate limit is {count:d} requests per minute"))
def rate_limit(options, count):
    options["RATE_LIMIT_PER_MINUTE"] = count


@when(parsers.parse('I ask "{question}"'))
def ask(app, outcome, question):
    outcome["response"] = app.client.post("/ask", json={"question": question})


@when(parsers.parse('I request "{path}"'))
def request_path(app, outcome, path):
    outcome["response"] = app.client.get(path)
    outcome.setdefault("all", []).append(outcome["response"])


@when(parsers.parse('"{name}" asks "{question}"'))
def client_asks(app, outcome, name, question):
    outcome["response"] = _ask(app, name, question)


@when(parsers.parse('"{name}" asks "{question}" {count:d} times'))
def client_asks_many(app, outcome, name, question, count):
    for _ in range(count):
        outcome["response"] = _ask(app, name, question)


@when(parsers.parse('I start production with {name} "{value}"'))
def start_production(outcome, name, value):
    env = settings_for({**VALID_PRODUCTION, name: value})
    try:
        create_app(config=load_config(env), model=ScriptedModel("{}"))
        outcome["error"] = None
    except ValueError as error:
        outcome["error"] = error
    outcome["secret"] = value.split(":")[-1]


@then(parsers.parse("the response status is {status:d}"))
def check_status(outcome, status):
    assert outcome["response"].status_code == status


@then(parsers.parse("every response status is {status:d}"))
def check_every_status(outcome, status):
    assert [r.status_code for r in outcome["all"]] == [status] * len(outcome["all"])


@then(parsers.parse('the response detail is "{detail}"'))
def check_detail(outcome, detail):
    assert outcome["response"].json()["detail"] == detail


@then("the response has a positive Retry-After header")
def has_retry_after(outcome):
    assert int(outcome["response"].headers["Retry-After"]) > 0


@then(parsers.parse('"{name}" can still ask a question'))
def other_client_passes(app, name):
    assert _ask(app, name).status_code == 200


@then(parsers.parse('"{name}" can ask again after {seconds:d} seconds'))
def client_recovers(app, clock, name, seconds):
    clock.advance(seconds)
    assert _ask(app, name).status_code == 200


@then(parsers.parse('the agent run and audit events name the client "{name}"'))
def events_name_client(app, name):
    for event_name in ("agent_run", "audit"):
        events = app.events(event_name)
        assert events, f"no {event_name} event was logged"
        assert all(event["client"] == name for event in events)


@then(parsers.parse('the log and the response do not contain the key of "{name}"'))
def key_is_not_leaked(app, outcome, name):
    assert KEYS[name] not in str(app.events())
    assert KEYS[name] not in outcome["response"].text


@then("the startup is refused")
def startup_refused(outcome):
    assert isinstance(outcome["error"], ValueError)


@then("the refusal does not show the key")
def refusal_hides_key(outcome):
    assert outcome["secret"] not in str(outcome["error"])
