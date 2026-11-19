"""Unit tests for the metrics endpoint and the Metrics class."""

import os

from conftest import BrokenModel, TickingClock

from app.metrics import Metrics, percentile

QUESTION = {"question": "Who is PRD-0004?"}


def test_metrics_include_the_process_id_and_the_default_slo_target(client):
    metrics = client.get("/metrics").json()
    assert metrics["pid"] == os.getpid()
    assert metrics["slo"]["p95_ms_target"] == 2000
    assert metrics["slo"]["met"] is True


def test_error_rate_is_zero_without_failures_and_positive_after_one(
    make_logged_app,
):
    healthy = make_logged_app()
    healthy.client.post("/ask", json=QUESTION)
    assert healthy.client.get("/metrics").json()["error_rate"] == 0
    broken = make_logged_app(model=BrokenModel())
    broken.client.post("/ask", json=QUESTION)
    assert broken.client.get("/metrics").json()["error_rate"] > 0


def test_slo_is_not_met_when_latency_exceeds_the_target(make_logged_app):
    slow = TickingClock(step=5)
    app = make_logged_app(clock=slow, SLO_P95_MS=100)
    app.client.post("/ask", json=QUESTION)
    slo = app.client.get("/metrics").json()["slo"]
    assert slo["p95_ms_target"] == 100
    assert slo["met"] is False


def test_slo_needs_the_p95_strictly_below_the_target():
    metrics = Metrics(100)
    metrics.record_request(100)
    assert metrics.snapshot()["slo"]["met"] is False


def test_percentile_uses_the_nearest_rank_and_handles_no_samples():
    samples = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert percentile(samples, 0.50) == 50
    assert percentile(samples, 0.95) == 100
    assert percentile([], 0.95) == 0
