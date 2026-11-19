"""Interfaz del modelo y modelo simulado determinista."""

import json
import re
from typing import Optional, Protocol, Sequence

TOOL_RESULT_PREFIX = "Resultado de la herramienta:"
HELP_MESSAGE = "Pregúntame por un producto (PRD-0001) o una categoría."
_PRODUCT_ID = re.compile(r"PRD-\d{4}")


SYSTEM_PROMPT = (
    "Eres el asistente de catálogo de productos. Responde únicamente con un objeto "
    "JSON, sin ningún texto fuera de él.\n"
    "Tienes dos herramientas de solo lectura:\n"
    "- get_product: busca un producto por su id. Argumento: product_id "
    "(por ejemplo PRD-0001). Ejemplo: "
    '{"tool": "get_product", "args": {"product_id": "PRD-0001"}}\n'
    "- search_by_category: lista los productos de una categoría. "
    "Argumento: category. Ejemplo: "
    '{"tool": "search_by_category", "args": {"category": "Hogar"}}\n'
    "Cuando ya tengas la información necesaria, responde con "
    '{"answer": "tu respuesta en español"}.'
)


class ModelUnavailable(Exception):
    """El modelo no pudo responder (red, HTTP o respuesta inválida).

    :param message: Texto corto sin datos sensibles (por ejemplo el tipo de error).
    :param status_code: Código HTTP del gateway, si lo hubo.
    :type status_code: int or None
    """

    def __init__(self, message: str = "", status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class Completion(str):
    """Respuesta de un modelo: el texto más sus tokens y si salió del caché.

    Es un ``str`` para que quien solo necesita el texto siga funcionando.

    :param text: Texto de la respuesta.
    :param input_tokens: Tokens de entrada.
    :param output_tokens: Tokens de salida.
    :param cached: Si la llamada se sirvió desde el caché del gateway.
    """

    input_tokens: int
    output_tokens: int
    cached: bool

    def __new__(
        cls, text: str, input_tokens: int, output_tokens: int, cached: bool = False
    ):
        instance = super().__new__(cls, text)
        instance.input_tokens = input_tokens
        instance.output_tokens = output_tokens
        instance.cached = cached
        return instance

    @property
    def text(self) -> str:
        """Texto de la respuesta como ``str`` simple.

        :return: El texto.
        :rtype: str
        """
        return str(self)


class Model(Protocol):
    """Interfaz que debe cumplir cualquier modelo."""

    def complete(
        self, messages: Sequence[dict], model: Optional[str] = None
    ) -> Completion:
        """Responde con un objeto JSON en texto, más tokens y caché.

        :param messages: Conversación como lista de ``{"role", "content"}``.
        :param model: Nombre del modelo elegido por el enrutador.
        :return: ``{"tool", "args"}`` o ``{"answer"}`` serializado.
        """


def count_tokens(text: str) -> int:
    """Cuenta tokens de forma aproximada: una palabra es un token.

    :param text: Texto a medir.
    :type text: str
    :return: Número de palabras.
    :rtype: int
    """
    return len(text.split())


class FakeModel:
    """Modelo simulado: reglas fijas sobre el último mensaje.

    :param catalog: Catálogo, usado para conocer las categorías.
    """

    def __init__(self, catalog) -> None:
        self._catalog = catalog

    def complete(
        self, messages: Sequence[dict], model: Optional[str] = None
    ) -> Completion:
        """Decide la respuesta con las reglas de la especificación.

        Responde igual con cualquier nombre de modelo; los tokens se cuentan
        como palabras y nunca hay caché.

        :param messages: Conversación completa.
        :type messages: Sequence[dict]
        :param model: Nombre del modelo simulado (no cambia la respuesta).
        :type model: str or None
        :return: Objeto JSON en texto con sus tokens.
        :rtype: Completion
        """
        del model
        text = self._decide(messages)
        tokens_in = sum(count_tokens(str(m["content"])) for m in messages)
        return Completion(text, tokens_in, count_tokens(text), False)

    def _decide(self, messages: Sequence[dict]) -> str:
        """Elige la respuesta según el último mensaje.

        :param messages: Conversación completa.
        :return: Objeto JSON en texto.
        :rtype: str
        """
        last = str(messages[-1]["content"]) if messages else ""
        if last.startswith(TOOL_RESULT_PREFIX):
            result = last[len(TOOL_RESULT_PREFIX):].strip()
            return self._dump({"answer": f"Según el catálogo: {result}"})
        found = _PRODUCT_ID.search(last)
        if found:
            return self._dump(
                {"tool": "get_product", "args": {"product_id": found.group(0)}}
            )
        lowered = last.casefold()
        for category in self._catalog.categories():
            if category.casefold() in lowered:
                args = {"category": category}
                return self._dump({"tool": "search_by_category", "args": args})
        return self._dump({"answer": HELP_MESSAGE})

    @staticmethod
    def _dump(payload: dict) -> str:
        """Serializa a JSON sin escapar caracteres no ASCII.

        :param payload: Objeto a serializar.
        :return: Texto JSON.
        """
        return json.dumps(payload, ensure_ascii=False)
