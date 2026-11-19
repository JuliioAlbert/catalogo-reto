"""Enrutador: una regla en código elige el modelo para cada pregunta."""

from typing import Tuple

# Se buscan como subcadena, sin distinguir mayúsculas.
LARGE_KEYWORDS = ("compara", "resume", "explica", "por qué", "analiza", "todos")


def choose_model(question: str, config) -> Tuple[str, str]:
    """Elige el modelo capaz o el barato para una pregunta.

    Usa el modelo capaz si el enrutamiento está apagado, si la pregunta pasa de
    ``router_max_chars`` caracteres o si contiene alguna palabra clave.

    :param question: Pregunta de la persona.
    :type question: str
    :param config: Configuración con ``routing``, ``router_max_chars`` y modelos.
    :type config: Config
    :return: Nombre del modelo y motivo de la elección.
    :rtype: tuple[str, str]
    """
    if not config.routing:
        return config.model_large, "routing disabled"
    if len(question) > config.router_max_chars:
        return config.model_large, f"long question (over {config.router_max_chars})"
    lowered = question.casefold()
    for keyword in LARGE_KEYWORDS:
        if keyword in lowered:
            return config.model_large, f"keyword: {keyword}"
    return config.model_small, "short simple question"
