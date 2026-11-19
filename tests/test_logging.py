"""Unit tests for the JSON event log written by the API and the agent."""

from datetime import datetime

from conftest import WALL_TIME, BrokenModel, ScriptedModel, final_answer, tool_call

QUESTION = "Who is PRD-0004?"
SECRET_QUESTION = "Tell me about the stock of Audifonos Studio"


def test_every_log_line_is_json_with_the_required_fields(make_logged_app):
    app = make_logged_app()
    headers = {"X-Request-ID": "r1"}
    app.client.post("/ask", json={"question": QUESTION}, headers=headers)
    events = app.events()
    assert events
    for event in events:
        assert {"ts", "service", "event", "request_id"} <= set(event)
        assert event["request_id"] == "r1"


def test_timestamp_is_iso_8601_utc_from_the_injected_clock(make_logged_app):
    app = make_logged_app()
    app.client.get("/health")
    stamp = datetime.fromisoformat(app.events("request")[0]["ts"])
    assert stamp == WALL_TIME
    assert stamp.utcoffset().total_seconds() == 0


def test_service_name_comes_from_the_configuration(make_logged_app):
    app = make_logged_app(SERVICE_NAME="people-bot")
    app.client.get("/health")
    assert app.events("request")[0]["service"] == "people-bot"


def test_service_name_defaults_to_catalog_assistant(make_logged_app):
    app = make_logged_app()
    app.client.get("/health")
    assert app.events("request")[0]["service"] == "product-catalog"


def test_each_request_leaves_one_request_event(make_logged_app):
    app = make_logged_app()
    app.client.get("/health")
    app.client.post("/ask", json={"question": ""})
    events = app.events("request")
    assert [(e["path"], e["status"]) for e in events] == [
        ("/health", 200),
        ("/ask", 422),
    ]
    assert all(e["method"] in {"GET", "POST"} for e in events)


def test_request_event_reports_latency_from_the_injected_clock(make_logged_app):
    app = make_logged_app()
    app.client.get("/health")
    assert app.events("request")[0]["latency_ms"] > 0


def test_agent_run_event_counts_but_never_quotes_the_question(make_logged_app):
    app = make_logged_app()
    history = [{"role": "user", "content": "Earlier private message"}]
    app.client.post("/ask", json={"question": SECRET_QUESTION, "history": history})
    run = app.events("agent_run")[0]
    assert run["question_chars"] == len(SECRET_QUESTION)
    assert run["history_messages"] == 1
    assert {"steps", "tools", "input_tokens", "output_tokens", "stopped"} <= set(run)
    log_text = str(app.events())
    assert "salary" not in log_text
    assert "Earlier private message" not in log_text


def test_each_tool_call_leaves_an_audit_event(make_logged_app):
    model = ScriptedModel(
        tool_call("get_product", product_id="PRD-0004"), final_answer("done")
    )
    app = make_logged_app(model=model)
    app.client.post("/ask", json={"question": QUESTION})
    audits = app.events("audit")
    assert len(audits) == 1
    assert audits[0]["action"] == "tool_call"
    assert audits[0]["tool"] == "get_product"
    assert audits[0]["args"] == {"product_id": "PRD-0004"}


def test_agent_run_says_when_the_step_cap_stopped_the_agent(make_logged_app):
    loop = ScriptedModel(tool_call("get_product", product_id="PRD-0001"))
    capped = make_logged_app(model=loop, AGENT_MAX_STEPS=1)
    capped.client.post(
        "/ask", json={"question": QUESTION}, headers={"X-Request-ID": "capped"}
    )
    finished = make_logged_app(model=ScriptedModel(final_answer("hi")))
    finished.client.post(
        "/ask", json={"question": QUESTION}, headers={"X-Request-ID": "finished"}
    )
    runs = {e["request_id"]: e for e in capped.events("agent_run")}
    assert runs["capped"]["stopped"]
    assert not runs["finished"]["stopped"]


def test_internal_failure_returns_500_with_the_request_id(make_logged_app):
    app = make_logged_app(model=BrokenModel())
    response = app.client.post(
        "/ask", json={"question": QUESTION}, headers={"X-Request-ID": "boom-1"}
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "internal error", "request_id": "boom-1"}
    assert response.headers["X-Request-ID"] == "boom-1"


def test_error_event_has_the_error_type_but_not_its_message(make_logged_app):
    app = make_logged_app(model=BrokenModel())
    app.client.post("/ask", json={"question": QUESTION})
    errors = app.events("error")
    assert len(errors) == 1
    assert "RuntimeError" in str(errors[0])
    assert "super-secret-detail" not in str(app.events())


def test_langsmith_key_never_reaches_the_log(make_logged_app, monkeypatch):
    # The autouse fake_langsmith fixture replaces the real client: no network.
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-key-should-stay-hidden")
    app = make_logged_app(LANGSMITH_TRACING="true")
    app.client.post("/ask", json={"question": QUESTION})
    assert "ls-key-should-stay-hidden" not in str(app.events())


def test_tracing_without_a_key_works_and_opens_no_connection(
    make_logged_app, monkeypatch
):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    def refuse(*_args, **_kwargs):
        raise AssertionError("the product tried to connect to the network")

    monkeypatch.setattr("socket.socket.connect", refuse)
    app = make_logged_app(LANGSMITH_TRACING="true")
    assert app.client.post("/ask", json={"question": QUESTION}).status_code == 200
