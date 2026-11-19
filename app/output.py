"""Validación de la respuesta del modelo antes de entregarla."""

from typing import Optional

SAFE_ANSWER = "No pude generar una respuesta segura. Intenta con otra pregunta."


def rejection_reason(answer, max_chars: int) -> Optional[str]:
    """Dice por qué una respuesta no se puede entregar, o ``None`` si sirve.

    :param answer: Texto que produjo el agente.
    :param max_chars: Largo máximo permitido.
    :type max_chars: int
    :return: ``not_text``, ``empty``, ``too_long`` o ``None``.
    :rtype: str or None
    """
    if not isinstance(answer, str):
        return "not_text"
    if not answer.strip():
        return "empty"
    if len(answer) > max_chars:
        return "too_long"
    return None
