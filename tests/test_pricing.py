"""Unit tests for app.pricing: cost from a per-million-token price table."""

import json

import pytest
from conftest import LARGE_MODEL, SMALL_MODEL

from app.pricing import PriceTable


def write_prices(tmp_path, models):
    path = tmp_path / "prices.json"
    path.write_text(json.dumps({"models": models}), encoding="utf-8")
    return path


def test_cost_uses_the_price_per_million_tokens_and_cached_calls_are_free(tmp_path):
    path = write_prices(
        tmp_path,
        {"m": {"input": 2.0, "output": 10.0}, "fake": {"input": 0, "output": 0}},
    )
    prices = PriceTable(path)
    cost = prices.cost_usd("m", 500_000, 100_000, cached=False)
    assert cost == pytest.approx(1.0 + 1.0)
    assert prices.cost_usd("m", 500_000, 100_000, cached=True) == 0
    assert prices.cost_usd("fake", 1000, 1000, cached=False) == 0


def test_shipped_prices_make_the_large_model_cost_more():
    from conftest import PRICES_PATH  # pylint: disable=import-outside-toplevel

    prices = PriceTable(PRICES_PATH)
    small = prices.cost_usd(SMALL_MODEL, 1000, 1000, cached=False)
    large = prices.cost_usd(LARGE_MODEL, 1000, 1000, cached=False)
    assert 0 < small < large


def test_unknown_model_and_bad_files_are_rejected(tmp_path):
    prices = PriceTable(write_prices(tmp_path, {"m": {"input": 1, "output": 1}}))
    with pytest.raises(ValueError):
        prices.cost_usd("other", 1, 1, cached=False)
    with pytest.raises((ValueError, OSError)):
        PriceTable(tmp_path / "missing.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        PriceTable(broken)
