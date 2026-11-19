"""Shared fixtures for the Catálogo de Productos tests.

Assumed interfaces (see the QA hand-off report):

- ``app.config.load_config(env: Mapping[str, str])`` returns an object with
  ``model_provider``, ``agent_max_steps``, ``max_question_chars``,
  ``products_path``, ``slo_p95_ms``, ``service_name``, ``langsmith_tracing``,
  ``hide_inputs`` and ``hide_outputs``; invalid values raise ``ValueError``.
- ``app.catalog.Catalog(path)`` with ``get_product`` and
  ``search_by_category``.
- ``app.llm.FakeModel(catalog)`` with ``complete(messages) -> str`` (JSON).
- ``app.agent.Agent(model=, catalog=, max_steps=).run(question, history=None)``
  returning an object (or dict) with ``answer``, ``steps`` and ``tools_used``.
- ``app.main.create_app(config=, model=, catalog=, clock=, wall_clock=)``.
  ``clock`` is a monotonic clock in seconds and ``wall_clock`` returns a timezone
  aware ``datetime``. Both are injected so the tests are deterministic.
- Events are written to standard output, one JSON object per line.

Session 4 interfaces:

- ``load_config`` also returns ``environment``, ``api_keys`` (dict
  client -> key, hidden from ``repr``) and ``rate_limit_per_minute``.
- ``app.auth.parse_api_keys(text) -> dict``; ``ValueError`` on bad entries.
- ``app.ratelimit.RateLimiter(limit, clock).check(client) -> int``: 0 when
  the request passes, otherwise the ``Retry-After`` seconds.
- ``app.compliance.check(config) -> list[str]`` of broken rules.
- ``create_app`` feeds its ``clock`` argument to the rate limiter and raises
  ``ValueError`` when production compliance fails.
- ``scripts/smoke.py`` exposes ``smoke(url, key, client) -> bool``.
"""

import json
import os
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

# Must run before app.main is imported so pytest never loads the real .env.
os.environ.setdefault("CATALOG_SKIP_DOTENV", "1")

# pylint: disable=wrong-import-position
import pytest
from fastapi.testclient import TestClient

from app.config import load_config
from app.catalog import Catalog
from app.llm import Completion, FakeModel
from app.main import create_app

PRODUCT_DIR = Path(__file__).resolve().parents[1]
PRODUCTS_PATH = PRODUCT_DIR / "data" / "products.json"
PRICES_PATH = PRODUCT_DIR / "data" / "model_prices.json"
SMALL_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"
LARGE_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
WALL_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
# Session 4: two clients with keys of 16 characters or more.
KEYS = {"alice": "alice-test-key-0001", "bob": "bob-test-key-000002"}
ALICE_KEY = KEYS["alice"]


class ScriptedModel:
    """Modelo de prueba: devuelve las respuestas guardadas, en orden.

    Session 3 interface: ``complete(messages, model)`` returns a ``Completion``.
    """

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.models = []

    def complete(self, messages, model=None):
        """Return the next scripted reply, repeating the last one."""
        self.calls.append(list(messages))
        self.models.append(model)
        index = min(len(self.calls) - 1, len(self.replies) - 1)
        text = self.replies[index]
        words_in = sum(len(str(m["content"]).split()) for m in messages)
        return Completion(
            text=text,
            input_tokens=words_in,
            output_tokens=len(text.split()),
            cached=False,
        )


class BrokenModel:
    """A model that always fails with a recognizable error."""

    def complete(self, _messages, _model=None):
        """Raise an error whose message must never reach the log."""
        raise RuntimeError("super-secret-detail")


class TickingClock:
    """A monotonic clock that advances by ``step`` seconds on every call."""

    def __init__(self, step=0.01):
        self.now = 0.0
        self.step = step

    def __call__(self):
        self.now += self.step
        return self.now


class FakeClock:
    """A clock that only moves when the test calls ``advance``."""

    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        """Move the clock forward without waiting."""
        self.now += seconds


class LoggedApp:
    """A test client plus the JSON events the app wrote to standard output."""

    def __init__(self, client, capsys):
        self.client = client
        self._capsys = capsys
        self._seen = []

    def events(self, name=None):
        """Return every event logged so far, optionally only those of ``name``."""
        text = self._capsys.readouterr().out
        self._seen.extend(json.loads(line) for line in text.splitlines() if line)
        if name is None:
            return list(self._seen)
        return [e for e in self._seen if e["event"] == name]


def tool_call(name, **args):
    """Build the JSON text a model sends to ask for a tool."""
    return json.dumps({"tool": name, "args": args})


def final_answer(text):
    """Build the JSON text a model sends to answer."""
    return json.dumps({"answer": text})


def field(result, name):
    """Read ``name`` from a result that may be a dict or an object."""
    if isinstance(result, dict):
        return result[name]
    return getattr(result, name)


def settings_for(overrides):
    """Build an environment mapping with the fake model and given overrides."""
    settings = {
        "MODEL_PROVIDER": "fake",
        "PRODUCTS_PATH": str(PRODUCTS_PATH),
        "PRICES_PATH": str(PRICES_PATH),
        "API_KEYS": ",".join(f"{name}:{key}" for name, key in KEYS.items()),
    }
    settings.update({key: str(value) for key, value in overrides.items()})
    return settings


class FakeLangsmith:
    """Stand-in for the langsmith pieces the tracer uses; never opens a socket."""

    def __init__(self):
        self.client_keys = []
        self.traced_names = []
        self.extras = []

    def install(self, monkeypatch):
        """Replace Client, traceable and tracing_context in the real module."""
        import langsmith  # pylint: disable=import-outside-toplevel

        outer = self

        class FakeClient:
            """A client that only remembers the key it was given."""

            def __init__(self, api_key=None, **_kwargs):
                outer.client_keys.append(api_key)

        def traceable(name=None, **_kwargs):
            outer.traced_names.append(name)

            def decorate(func):
                def traced(*args, **kwargs):
                    outer.extras.append(kwargs.pop("langsmith_extra", None))
                    return func(*args, **kwargs)

                return traced

            return decorate

        def fake_context(**_kwargs):
            return nullcontext()

        monkeypatch.setattr(langsmith, "Client", FakeClient)
        monkeypatch.setattr(langsmith, "traceable", traceable)
        monkeypatch.setattr(langsmith, "tracing_context", fake_context)


@pytest.fixture(name="fake_langsmith", autouse=True)
def fake_langsmith_fixture(monkeypatch):
    """Keep every test off the network, even when tracing is switched on."""
    fake = FakeLangsmith()
    try:
        fake.install(monkeypatch)
    except ImportError:
        pass
    return fake


@pytest.fixture(name="catalog")
def catalog_fixture():
    """The real product catalog loaded from the product data."""
    return Catalog(PRODUCTS_PATH)


@pytest.fixture(name="make_client")
def make_client_fixture(catalog):
    """Factory of test clients with the fake model and given settings."""

    def build(model=None, key=ALICE_KEY, clock=None, **env):
        """Build a client that sends ``key`` by default (``None``: no key)."""
        config = load_config(settings_for(env))
        app = create_app(
            config=config,
            model=model or FakeModel(catalog),
            catalog=catalog,
            **({"clock": clock} if clock else {}),
        )
        return TestClient(app, headers={"X-API-Key": key} if key else {})

    return build


@pytest.fixture(name="client")
def client_fixture(make_client):
    """A test client with the default configuration."""
    return make_client()


@pytest.fixture(name="make_logged_app")
def make_logged_app_fixture(catalog, capsys):
    """Factory of apps whose log can be read back, with injected clocks."""

    def build(model=None, clock=None, key=ALICE_KEY, **env):
        app = create_app(
            config=load_config(settings_for(env)),
            model=model or FakeModel(catalog),
            catalog=catalog,
            clock=clock or TickingClock(),
            wall_clock=lambda: WALL_TIME,
        )
        client = TestClient(
            app,
            raise_server_exceptions=False,
            headers={"X-API-Key": key} if key else {},
        )
        return LoggedApp(client, capsys)

    return build
