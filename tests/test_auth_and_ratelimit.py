"""Unit tests for API key parsing and the per-client rate limiter."""

import pytest
from conftest import FakeClock

from app.auth import parse_api_keys
from app.ratelimit import RateLimiter


def test_several_clients_are_parsed_ignoring_spaces_and_empty_text():
    keys = parse_api_keys(" alice:key-aaaa , bob:key-bbbb ")
    assert keys == {"alice": "key-aaaa", "bob": "key-bbbb"}
    assert not parse_api_keys("")


@pytest.mark.parametrize(
    "text, secret, length",
    [
        ("alice:key-aaaa,bobsecretvalue", "bobsecretvalue", 14),
        ("alice:key-aaaa,:onlysecretkey123", "onlysecretkey123", 17),
    ],
)
def test_malformed_entry_is_reported_with_its_length_but_not_its_value(
    text, secret, length
):
    with pytest.raises(ValueError) as error:
        parse_api_keys(text)
    message = str(error.value)
    assert "2" in message and str(length) in message
    assert secret not in message


def test_limit_is_exact_and_retry_after_is_rounded_up():
    clock = FakeClock()
    limiter = RateLimiter(2, clock)
    assert limiter.check("alice") == 0
    assert limiter.check("alice") == 0
    clock.advance(29.5)
    assert limiter.check("alice") == 31


def test_window_slides_so_old_requests_stop_counting():
    clock = FakeClock()
    limiter = RateLimiter(2, clock)
    limiter.check("alice")
    limiter.check("alice")
    assert limiter.check("alice") > 0
    clock.advance(61)
    assert limiter.check("alice") == 0


def test_clients_have_independent_counters():
    limiter = RateLimiter(1, FakeClock())
    assert limiter.check("alice") == 0
    assert limiter.check("alice") > 0
    assert limiter.check("bob") == 0
