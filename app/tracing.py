"""Trazas opcionales en LangSmith; apagadas si falta la clave o la opción."""

import logging
from typing import Any, Callable, Mapping, Optional

LOGGER = logging.getLogger("catalog_assistant.tracing")


def _hide(_payload: Any) -> dict:
    """Oculta por completo las entradas o salidas de una traza.

    :param _payload: Contenido original (se descarta).
    :return: Diccionario vacío.
    :rtype: dict
    """
    return {}


class Tracer:
    """Envuelve llamadas con ``@traceable`` solo si las trazas están activas.

    Sin clave de LangSmith no se importa la librería ni se abre conexión.

    :param enabled: Si las trazas están encendidas y hay clave.
    :type enabled: bool
    :param hide_inputs: No mandar las entradas.
    :type hide_inputs: bool
    :param hide_outputs: No mandar las salidas.
    :type hide_outputs: bool
    :param api_key: Clave de LangSmith (nunca se escribe en el log).
    :type api_key: str or None
    """

    def __init__(
        self,
        enabled: bool = False,
        hide_inputs: bool = True,
        hide_outputs: bool = True,
        api_key: Optional[str] = None,
    ) -> None:
        self._enabled = enabled and bool(api_key)
        self._hide_inputs = hide_inputs
        self._hide_outputs = hide_outputs
        self._api_key = api_key
        self._module: Any = None
        self._client: Any = None

    @classmethod
    def from_config(cls, config, env: Mapping[str, str]) -> "Tracer":
        """Crea el trazador con la configuración y el entorno.

        :param config: Configuración con ``langsmith_tracing`` y ``hide_*``.
        :param env: Variables de entorno (de ahí se lee la clave).
        :type env: Mapping[str, str]
        :return: El trazador.
        :rtype: Tracer
        """
        return cls(
            enabled=config.langsmith_tracing,
            hide_inputs=config.hide_inputs,
            hide_outputs=config.hide_outputs,
            api_key=env.get("LANGSMITH_API_KEY"),
        )

    @property
    def enabled(self) -> bool:
        """Indica si las trazas están activas.

        :return: ``True`` si se mandarán trazas.
        :rtype: bool
        """
        return self._enabled

    def _prepare(self) -> bool:
        """Importa langsmith y crea el cliente la primera vez.

        :return: ``True`` si se puede trazar.
        :rtype: bool
        """
        if not self._enabled:
            return False
        if self._module is None:
            try:
                import langsmith  # pylint: disable=import-outside-toplevel

                self._client = langsmith.Client(
                    api_key=self._api_key,
                    hide_inputs=_hide if self._hide_inputs else None,
                    hide_outputs=_hide if self._hide_outputs else None,
                )
                self._module = langsmith
            except Exception as error:  # pylint: disable=broad-exception-caught
                LOGGER.warning("tracing disabled: %s", type(error).__name__)
                self._enabled = False
                return False
        return True

    def call(
        self,
        name: str,
        run_type: str,
        func: Callable,
        request_id: Optional[str],
        *args,
        client: Optional[str] = None,
        **kwargs,
    ):
        """Ejecuta ``func``, como traza si LangSmith está activo.

        :param name: Nombre de la traza.
        :type name: str
        :param run_type: Tipo de corrida (``chain``, ``llm`` o ``tool``).
        :type run_type: str
        :param func: Función a ejecutar.
        :type func: Callable
        :param request_id: Id de la petición, va en los metadatos.
        :type request_id: str or None
        :param client: Nombre del cliente, va en los metadatos (nunca su clave).
        :type client: str or None
        :return: Lo que devuelva ``func``.
        """
        if not self._prepare():
            return func(*args, **kwargs)
        module = self._module
        decorator = module.traceable(
            name=name, run_type=run_type, client=self._client
        )
        traced = decorator(func)
        extra = {"metadata": {"request_id": request_id, "client": client}}
        with module.tracing_context(enabled=True):
            return traced(*args, langsmith_extra=extra, **kwargs)
