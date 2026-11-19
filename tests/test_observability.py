"""Unit tests for request tracing and metrics in the API."""

import uuid

QUESTION = {"question": "Who is PRD-0004?"}


def test_health_response_has_a_generated_request_id(client):
    response = client.get("/health")
    assert uuid.UUID(response.headers["X-Request-ID"])


def test_client_request_id_is_echoed_in_the_header(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-1"})
    assert response.headers["X-Request-ID"] == "abc-1"


def test_ask_body_contains_the_request_id(client):
    response = client.post("/ask", json=QUESTION, headers={"X-Request-ID": "q-7"})
    assert response.json()["request_id"] == "q-7"


def test_rejected_request_still_carries_a_request_id(client):
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 422
    assert "X-Request-ID" in response.headers


def test_metrics_report_the_expected_shape(client):
    client.post("/ask", json=QUESTION)
    metrics = client.get("/metrics").json()
    assert set(metrics["latency_ms"]) == {"p50", "p95"}
    assert metrics["latency_ms"]["p95"] >= metrics["latency_ms"]["p50"] >= 0
    assert isinstance(metrics["slo"]["met"], bool)


def test_metrics_requests_and_tokens_grow_with_each_question(client):
    client.post("/ask", json=QUESTION)
    first = client.get("/metrics").json()
    client.post("/ask", json=QUESTION)
    second = client.get("/metrics").json()
    assert second["requests"] > first["requests"]
    assert second["tokens"]["input"] > first["tokens"]["input"] > 0


def test_home_page_shows_the_request_id(client):
    assert "request_id" in client.get("/").text
