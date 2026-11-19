"""Unit tests for scripts/load_test.py with a simulated transport."""

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import load_test  # pylint: disable=wrong-import-position,import-error


def _transport(statuses):
    calls = iter(statuses)

    def handler(_request):
        status = next(calls)
        body = {"cost_usd": 0.5} if status == 200 else {"detail": "x"}
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def test_summary_counts_ok_rate_limited_and_errors():
    transport = _transport([200, 200, 429, 500])
    summary = asyncio.run(load_test.run("http://t", "k", 4, 2, transport))
    assert (summary["ok"], summary["rate_limited"], summary["errors"]) == (2, 1, 1)
    assert summary["cost_usd"] == 1.0


def test_percentile_of_empty_list_is_zero():
    assert load_test.percentile([], 0.95) == 0.0


def test_percentile_picks_the_ranked_value():
    assert load_test.percentile([10, 20, 30, 40, 50], 0.5) == 30


def test_main_needs_url_and_key(monkeypatch):
    monkeypatch.delenv("SMOKE_API_KEY", raising=False)
    assert load_test.main(["http://t"]) == 2
