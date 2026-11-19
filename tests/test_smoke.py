"""Unit tests for scripts/smoke.py with a fake HTTP transport."""

import importlib.util
from pathlib import Path

import httpx
import pytest

SMOKE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "smoke.py"
URL = "https://catalog.example.com"
KEY = "smoke-key-0123456789"


@pytest.fixture(name="smoke_module")
def smoke_module_fixture():
    """Load scripts/smoke.py, which is not a package."""
    spec = importlib.util.spec_from_file_location("smoke", SMOKE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _client(keyed_status):
    """A client whose server answers 401 without key and ``keyed_status`` with."""

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.headers.get("X-API-Key") == KEY:
            return httpx.Response(keyed_status, json={})
        return httpx.Response(401, json={})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_smoke_prints_ok_for_each_of_the_three_checks(smoke_module, capsys):
    assert smoke_module.smoke(URL, KEY, _client(200)) is True
    output = capsys.readouterr().out
    assert output.count("[OK]") == 3
    assert "[FAIL]" not in output


def test_smoke_fails_and_never_prints_the_key_when_ask_is_rejected(
    smoke_module, capsys
):
    assert smoke_module.smoke(URL, KEY, _client(401)) is False
    output = capsys.readouterr().out
    assert "[FAIL]" in output
    assert KEY not in output
