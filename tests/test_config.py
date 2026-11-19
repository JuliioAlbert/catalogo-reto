"""Unit tests for app.config."""

import pytest

from app.config import load_config


def test_defaults_are_used_when_nothing_is_set():
    config = load_config({})
    assert config.model_provider == "fake"
    assert config.agent_max_steps == 5
    assert config.max_question_chars == 2000
    assert str(config.products_path).endswith("data/products.json")


def test_observability_defaults_are_safe():
    config = load_config({})
    assert config.service_name == "product-catalog"
    assert config.slo_p95_ms == 2000
    assert config.langsmith_tracing is False
    assert config.hide_inputs is True
    assert config.hide_outputs is True


def test_observability_variables_can_be_changed():
    config = load_config(
        {
            "SERVICE_NAME": "people-bot",
            "SLO_P95_MS": "500",
            "LANGSMITH_TRACING": "true",
            "HIDE_INPUTS": "false",
            "HIDE_OUTPUTS": "false",
        }
    )
    assert config.service_name == "people-bot"
    assert config.slo_p95_ms == 500
    assert config.langsmith_tracing is True
    assert config.hide_inputs is False
    assert config.hide_outputs is False


@pytest.mark.parametrize(
    "env",
    [
        {"AGENT_MAX_STEPS": "0"},
        {"SLO_P95_MS": "0"},
        {"LANGSMITH_TRACING": "maybe"},
        {"HIDE_INPUTS": "2"},
        {"AGENT_MAX_STEPS": "many"},
        {"MAX_QUESTION_CHARS": "-5"},
        {"MODEL_PROVIDER": "unknown-vendor"},
    ],
)
def test_invalid_values_prevent_startup(env):
    with pytest.raises(ValueError):
        load_config(env)
