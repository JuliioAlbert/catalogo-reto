"""Unit tests for production compliance and the new configuration."""

import pytest
from conftest import ScriptedModel, settings_for

from app import compliance
from app.config import load_config
from app.main import create_app

GOOD_KEY = "alice:abcdefghijklmnop"
SHORT_SECRET = "shortsecret1234"
PRODUCTION = {
    "ENVIRONMENT": "production",
    "MODEL_PROVIDER": "gateway",
    "CF_ACCOUNT_ID": "account",
    "CF_API_TOKEN": "cloudflare-token",
    "API_KEYS": GOOD_KEY,
}


def _production_config(**overrides):
    return load_config(settings_for({**PRODUCTION, **overrides}))


@pytest.mark.parametrize(
    "overrides, broken_rules",
    [
        ({}, 0),
        ({"API_KEYS": "alice:abcdefghijklmnop"}, 0),
        ({"MODEL_PROVIDER": "fake"}, 1),
        ({"API_KEYS": ""}, 1),
        ({"API_KEYS": f"alice:{SHORT_SECRET}"}, 1),
        ({"LANGSMITH_TRACING": "true", "HIDE_INPUTS": "false"}, 1),
        ({"LANGSMITH_TRACING": "true", "HIDE_OUTPUTS": "false"}, 1),
        ({"LANGSMITH_TRACING": "false", "HIDE_INPUTS": "false"}, 0),
    ],
)
def test_each_production_rule_is_checked_on_its_own(overrides, broken_rules):
    assert len(compliance.check(_production_config(**overrides))) == broken_rules


def test_production_start_lists_every_broken_rule_without_the_key():
    env = settings_for(
        {
            "ENVIRONMENT": "production",
            "MODEL_PROVIDER": "fake",
            "API_KEYS": f"alice:{SHORT_SECRET}",
            "LANGSMITH_TRACING": "true",
            "HIDE_INPUTS": "false",
        }
    )
    with pytest.raises(ValueError) as error:
        create_app(config=load_config(env), model=ScriptedModel("{}"))
    message = str(error.value)
    for name in ("MODEL_PROVIDER", "API_KEYS", "HIDE_INPUTS"):
        assert name in message
    assert SHORT_SECRET not in message


@pytest.mark.parametrize(
    "overrides",
    [
        {"ENVIRONMENT": "staging"},
        {"RATE_LIMIT_PER_MINUTE": "0"},
        {"RATE_LIMIT_PER_MINUTE": "many"},
    ],
)
def test_invalid_environment_or_rate_limit_is_rejected(overrides):
    with pytest.raises(ValueError):
        load_config(settings_for(overrides))


def test_new_settings_have_defaults_and_hide_the_keys_from_repr():
    config = load_config(settings_for({}))
    assert config.environment == "development"
    assert config.rate_limit_per_minute == 30
    assert "alice-test-key-0001" not in repr(config)
