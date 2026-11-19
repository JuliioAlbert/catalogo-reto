"""Steps for the scenarios in features/catalog_assistant.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/catalog_assistant.feature")


@pytest.fixture(name="settings")
def settings_fixture():
    """Environment overrides chosen by the Given steps."""
    return {}


@pytest.fixture(name="outcome")
def outcome_fixture():
    """Holds the last HTTP response."""
    return {}


@given(parsers.parse("the agent is limited to {count:d} step"))
def limit_steps(settings, count):
    settings["AGENT_MAX_STEPS"] = count


@when(parsers.parse('I ask "{question}"'))
def ask_question(make_client, settings, outcome, question):
    client = make_client(**settings)
    outcome["response"] = client.post("/ask", json={"question": question})


@when("I ask an empty question")
def ask_empty_question(make_client, settings, outcome):
    client = make_client(**settings)
    outcome["response"] = client.post("/ask", json={"question": ""})


@when(parsers.parse("I ask a question of {size:d} characters"))
def ask_long_question(make_client, settings, outcome, size):
    client = make_client(**settings)
    outcome["response"] = client.post("/ask", json={"question": "a" * size})


@when("I request the health check")
def request_health(client, outcome):
    outcome["response"] = client.get("/health")


@then(parsers.parse("the response status is {status:d}"))
def check_status(outcome, status):
    assert outcome["response"].status_code == status


@then(parsers.parse('the answer mentions "{text}"'))
def answer_mentions(outcome, text):
    assert text in outcome["response"].json()["answer"]


@then(parsers.parse('the answer does not mention "{text}"'))
def answer_does_not_mention(outcome, text):
    assert text not in outcome["response"].json()["answer"]


@then(parsers.parse('the answer is "{text}"'))
def answer_is(outcome, text):
    assert outcome["response"].json()["answer"] == text


@then(parsers.parse('the tools used are "{tool}"'))
def tools_used_are(outcome, tool):
    assert outcome["response"].json()["tools_used"] == [tool]


@then("no tools were used")
def no_tools_used(outcome):
    assert outcome["response"].json()["tools_used"] == []


@then(parsers.parse("the agent took {count:d} steps"))
def agent_steps(outcome, count):
    assert outcome["response"].json()["steps"] == count


@then(parsers.parse('the health status is "{status}"'))
def health_status(outcome, status):
    assert outcome["response"].json()["status"] == status


@then("the health check includes a process id")
def health_pid(outcome):
    assert isinstance(outcome["response"].json()["pid"], int)
