"""Reglas de compliance de producción, revisadas al arrancar."""

from typing import List

MIN_KEY_CHARS = 16


def check(config) -> List[str]:
    """Devuelve las reglas de producción que la configuración rompe.

    Los mensajes nombran la variable, nunca su valor. Con ``development``
    no hay reglas.

    :param config: Configuración con ``environment``, ``model_provider``,
        ``api_keys``, ``langsmith_tracing``, ``hide_inputs`` y ``hide_outputs``.
    :return: Una frase por regla rota; vacía si todo está bien.
    :rtype: list[str]
    """
    if config.environment != "production":
        return []
    broken = []
    if config.model_provider == "fake":
        broken.append("MODEL_PROVIDER must not be fake in production")
    if not config.api_keys:
        broken.append("API_KEYS must not be empty in production")
    short = sorted(
        name for name, key in config.api_keys.items() if len(key) < MIN_KEY_CHARS
    )
    if short:
        broken.append(
            f"API_KEYS keys must have at least {MIN_KEY_CHARS} characters "
            f"(too short for: {', '.join(short)})"
        )
    if config.langsmith_tracing:
        if not config.hide_inputs:
            broken.append("HIDE_INPUTS must be true when tracing is on")
        if not config.hide_outputs:
            broken.append("HIDE_OUTPUTS must be true when tracing is on")
    return broken
