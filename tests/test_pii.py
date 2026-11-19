"""Unit tests for app.pii."""

import pytest

from app import pii


@pytest.mark.parametrize(
    "text, kind",
    [
        ("Mi correo es ana.lopez@example.com", "email"),
        ("Llamame al 55 1234 5678", "phone"),
        ("Mi telefono +52 33-1234-5678", "phone"),
        ("RFC LOPA800101AB1", "rfc"),
        ("CURP LOPA800101HDFPRN09", "curp"),
        ("Tarjeta 4111 1111 1111 1111", "card"),
    ],
)
def test_each_kind_of_personal_data_is_detected(text, kind):
    assert pii.detect(text) == [kind]


def test_redact_replaces_the_value_and_never_returns_it():
    masked, types = pii.redact("Escribe a ana@example.com o al 5512345678")
    assert "ana@example.com" not in masked
    assert "5512345678" not in masked
    assert "[CORREO]" in masked and "[TELEFONO]" in masked
    assert types == ["email", "phone"]


@pytest.mark.parametrize(
    "text",
    ["Quien es PRD-0004", "Cuesta 18999 pesos", "Hay 12 piezas", "1234 5678 9012 3456"],
)
def test_catalog_text_and_invalid_card_numbers_are_not_flagged(text):
    assert not pii.detect(text)
