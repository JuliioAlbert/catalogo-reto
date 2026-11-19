"""Unit tests for app.gateway with a fake httpx transport (no network)."""

import json

import httpx
import pytest
from conftest import SMALL_MODEL, settings_for

from app.config import load_config
from app.gateway import GatewayModel
from app.llm import ModelUnavailable

REPLY = '{"answer": "hi"}'
MESSAGES = [{"role": "user", "content": "Hello"}]


def gateway_config(**extra):
    return load_config(
        settings_for(
            {
                "MODEL_PROVIDER": "gateway",
                "CF_ACCOUNT_ID": "acc1",
                "CF_GATEWAY_ID": "gw1",
                "CF_API_TOKEN": "tok-123",
                "MODEL_MAX_TOKENS": 77,
                "MODEL_TEMPERATURE": 0,
                **extra,
            }
        )
    )


def build_model(handler, **extra):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GatewayModel(gateway_config(**extra), client=client)


def ok_response(cache_status="MISS", prompt=11, completion=5):
    body = {
        "choices": [{"message": {"role": "assistant", "content": REPLY}}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    }
    return httpx.Response(200, json=body, headers={"cf-aig-cache-status": cache_status})


def test_request_has_the_documented_url_headers_and_body():
    seen = []

    def handler(request):
        seen.append(request)
        return ok_response()

    build_model(handler).complete(MESSAGES, SMALL_MODEL)
    request = seen[0]
    assert str(request.url) == (
        "https://gateway.ai.cloudflare.com/v1/acc1/gw1/"
        "workers-ai/v1/chat/completions"
    )
    assert request.headers["Authorization"] == "Bearer tok-123"
    assert request.headers["cf-aig-authorization"] == "Bearer tok-123"
    assert json.loads(request.content) == {
        "model": SMALL_MODEL,
        "messages": MESSAGES,
        "max_tokens": 77,
        "temperature": 0,
    }


def test_cache_ttl_header_is_sent_only_when_the_ttl_is_positive():
    seen = []

    def handler(request):
        seen.append(request)
        return ok_response()

    build_model(handler, CACHE_TTL_SECONDS=0).complete(MESSAGES, SMALL_MODEL)
    build_model(handler, CACHE_TTL_SECONDS=120).complete(MESSAGES, SMALL_MODEL)
    assert "cf-aig-cache-ttl" not in seen[0].headers
    assert seen[1].headers["cf-aig-cache-ttl"] == "120"


def test_usage_tokens_and_cache_status_are_read_from_the_response():
    miss = build_model(lambda r: ok_response("MISS", 11, 5))
    hit = build_model(lambda r: ok_response("HIT", 3, 2))
    first = miss.complete(MESSAGES, SMALL_MODEL)
    second = hit.complete(MESSAGES, SMALL_MODEL)
    assert (first.text, first.input_tokens, first.output_tokens) == (REPLY, 11, 5)
    assert first.cached is False
    assert second.cached is True


def test_the_token_never_appears_in_the_error_or_the_logs(caplog):
    model = build_model(lambda request: httpx.Response(401, text="denied"))
    with caplog.at_level("DEBUG"):
        with pytest.raises(ModelUnavailable) as error:
            model.complete(MESSAGES, SMALL_MODEL)
    assert "tok-123" not in str(error.value)
    assert "tok-123" not in caplog.text


def _raise_timeout(request):
    raise httpx.ReadTimeout("slow", request=request)


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500, text="boom"),
        _raise_timeout,
        lambda request: httpx.Response(200, text="not json"),
        lambda request: httpx.Response(200, json={"unexpected": True}),
    ],
    ids=["http-error", "timeout", "malformed-json", "missing-fields"],
)
def test_every_failure_becomes_model_unavailable(handler):
    with pytest.raises(ModelUnavailable):
        build_model(handler).complete(MESSAGES, SMALL_MODEL)
