"""Detección y enmascarado de datos personales (PII) en texto libre."""

import re
from typing import List, Tuple

# Cada patrón se enmascara con una etiqueta; el orden evita que un número
# largo se lea primero como teléfono.
_PATTERNS = (
    ("card", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), "[TARJETA]"),
    ("curp", re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", re.I), "[CURP]"),
    ("rfc", re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", re.I), "[RFC]"),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), "[CORREO]"),
    (
        "phone",
        re.compile(
            r"(?<!\d)(?:\+?52[ -]?)?(?:\d{2}[ -]?\d{4}[ -]?\d{4}"
            r"|\d{3}[ -]?\d{3}[ -]?\d{4})(?!\d)"
        ),
        "[TELEFONO]",
    ),
)
PII_TYPES = tuple(name for name, _pattern, _label in _PATTERNS)


def _passes_luhn(digits: str) -> bool:
    """Indica si una cadena de dígitos cumple el algoritmo de Luhn.

    :param digits: Solo dígitos.
    :type digits: str
    :return: ``True`` si la suma de comprobación es válida.
    :rtype: bool
    """
    total = 0
    for index, char in enumerate(reversed(digits)):
        number = int(char)
        if index % 2 == 1:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def _is_real_card(match: "re.Match[str]") -> bool:
    """Una tarjeta debe tener entre 13 y 19 dígitos y pasar Luhn.

    :param match: Coincidencia del patrón de tarjeta.
    :return: ``True`` si parece una tarjeta de verdad.
    :rtype: bool
    """
    digits = re.sub(r"\D", "", match.group(0))
    return 13 <= len(digits) <= 19 and _passes_luhn(digits)


def redact(text: str) -> Tuple[str, List[str]]:
    """Enmascara los datos personales de un texto.

    :param text: Texto a revisar.
    :type text: str
    :return: El texto enmascarado y los tipos encontrados (sin repetir, en
        orden de aparición de la lista de patrones). Nunca los valores.
    :rtype: tuple[str, list[str]]
    """
    found: List[str] = []
    for name, pattern, label in _PATTERNS:

        def replace(match, name=name, label=label):
            if name == "card" and not _is_real_card(match):
                return match.group(0)
            if name not in found:
                found.append(name)
            return label

        text = pattern.sub(replace, text)
    return text, found


def detect(text: str) -> List[str]:
    """Tipos de datos personales presentes en un texto.

    :param text: Texto a revisar.
    :type text: str
    :return: Tipos encontrados, vacía si no hay.
    :rtype: list[str]
    """
    return redact(text)[1]
