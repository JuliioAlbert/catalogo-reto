"""Unit tests for app.router: the rule that picks the model per question."""

import pytest
from conftest import LARGE_MODEL, SMALL_MODEL, settings_for

from app.config import load_config
from app.router import choose_model


def config_with(**env):
    return load_config(settings_for(env))


@pytest.mark.parametrize(
    "question",
    [
        "Compara Hogar con Deportes",
        "resume el producto PRD-0001",
        "explica la estructura",
        "¿por qué PRD-0002 cambió?",
        "analiza el equipo",
        "dame a todos",
        "¿POR QUÉ falla?",
    ],
)
def test_keywords_select_the_large_model_ignoring_case(question):
    model, reason = choose_model(question, config_with())
    assert model == LARGE_MODEL
    assert reason


def test_length_limit_is_inclusive_for_the_small_model():
    config = config_with(ROUTER_MAX_CHARS=80)
    assert choose_model("a" * 80, config)[0] == SMALL_MODEL
    assert choose_model("a" * 81, config)[0] == LARGE_MODEL


def test_disabled_routing_always_selects_the_large_model():
    model, reason = choose_model("Who is PRD-0001?", config_with(ROUTING="false"))
    keyword_reason = choose_model("compara", config_with())[1]
    assert model == LARGE_MODEL
    assert reason != keyword_reason
