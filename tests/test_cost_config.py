"""Unit tests for the session 3 settings in app.config."""

import pytest
from conftest import LARGE_MODEL, SMALL_MODEL, settings_for

from app.config import load_config

GATEWAY = {
    "MODEL_PROVIDER": "gateway",
    "CF_ACCOUNT_ID": "account",
    "CF_GATEWAY_ID": "gateway",
    "CF_API_TOKEN": "token-value",
}


def test_cost_settings_have_the_documented_defaults():
    config = load_config(settings_for({}))
    assert config.model_small == SMALL_MODEL
    assert config.model_large == LARGE_MODEL
    assert config.routing is True
    assert config.router_max_chars == 80
    assert config.history_window == 6
    assert config.model_max_tokens == 300
    assert config.model_temperature == 0
    assert config.cache_ttl_seconds == 0
    assert config.cf_gateway_id == "default"


@pytest.mark.parametrize(
    "name, value",
    [
        ("ROUTING", "maybe"),
        ("ROUTER_MAX_CHARS", "long"),
        ("HISTORY_WINDOW", "0"),
        ("MODEL_MAX_TOKENS", "-5"),
        ("MODEL_TEMPERATURE", "hot"),
        ("CACHE_TTL_SECONDS", "-1"),
    ],
)
def test_invalid_cost_settings_are_rejected(name, value):
    with pytest.raises(ValueError):
        load_config(settings_for({name: value}))


@pytest.mark.parametrize("missing", ["CF_ACCOUNT_ID", "CF_API_TOKEN"])
def test_gateway_provider_requires_the_cloudflare_variables(missing):
    env = {key: value for key, value in GATEWAY.items() if key != missing}
    with pytest.raises(ValueError):
        load_config(settings_for(env))
    assert load_config(settings_for(GATEWAY)).cf_api_token == "token-value"


def test_api_token_never_appears_in_the_config_repr():
    config = load_config(settings_for(GATEWAY))
    assert "token-value" not in repr(config)
    assert "token-value" not in str(config)
