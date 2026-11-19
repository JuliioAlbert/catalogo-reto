"""Agente con bucle acotado y dos herramientas de solo lectura."""

import json
from dataclasses import dataclass, field
from typing import List, Optional

from app.events import EventLogger
from app.config import MAX_HISTORY_ITEMS
from app.llm import SYSTEM_PROMPT, TOOL_RESULT_PREFIX
from app.tracing import Tracer

CAP_MESSAGE = "No pude completar la respuesta. Intenta con una pregunta más concreta."
# Argumento permitido por herramienta: solo ids y categorías van al audit.
AUDITED_ARGS = {"get_product": "product_id", "search_by_category": "category"}


@dataclass
class AgentResult:  # pylint: disable=too-many-instance-attributes
    """Resultado de una corrida del agente.

    :param answer: Texto de la respuesta.
    :param steps: Vueltas del bucle usadas.
    :param tools_used: Nombres de las herramientas ejecutadas, en orden.
    :param input_tokens: Tokens de entrada aproximados.
    :param output_tokens: Tokens de salida aproximados.
    :param stopped: Si el tope de vueltas cortó la corrida.
    :param model: Modelo que atendió la pregunta.
    :param route: Motivo del enrutador.
    :param cached_calls: Llamadas servidas desde el caché del gateway.
    :param cost_usd: Costo acumulado en USD, sin redondear.
    """

    answer: str
    steps: int
    tools_used: List[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stopped: bool = False
    model: str = ""
    route: str = ""
    cached_calls: int = 0
    cost_usd: float = 0.0


class Agent:
    """Bucle: el modelo pide una herramienta o responde, con tope de vueltas.

    :param model: Objeto con ``complete(messages) -> str``.
    :param catalog: Catálogo de productos.
    :param max_steps: Tope de vueltas del bucle.
    :param events: Registrador de eventos; si falta no se registra nada.
    :type events: EventLogger or None
    :param tracer: Trazador de LangSmith; por omisión apagado.
    :type tracer: Tracer or None
    :param prices: Tabla de precios; sin ella el costo es 0.
    :type prices: PriceTable or None
    :param history_window: Mensajes de historial que se mandan; sin valor o con
        ``MAX_HISTORY_ITEMS`` o más se manda todo el historial.
    :type history_window: int or None
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        model,
        catalog,
        max_steps: int,
        events: Optional[EventLogger] = None,
        tracer: Optional[Tracer] = None,
        prices=None,
        history_window: Optional[int] = None,
    ) -> None:
        self._model = model
        self._catalog = catalog
        self._max_steps = max_steps
        self._events = events
        self._tracer = tracer or Tracer()
        self._prices = prices
        self._history_window = history_window

    def run(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        question: str,
        history: Optional[list] = None,
        request_id: Optional[str] = None,
        model_name: Optional[str] = None,
        route: str = "",
        client: Optional[str] = None,
    ) -> AgentResult:
        """Responde una pregunta y registra el evento ``agent_run``.

        :param question: Pregunta de la persona.
        :type question: str
        :param history: Mensajes previos que manda el cliente.
        :type history: list[dict] or None
        :param request_id: Id de la petición, para el log y las trazas.
        :type request_id: str or None
        :param model_name: Modelo elegido por el enrutador.
        :type model_name: str or None
        :param route: Motivo de la elección del modelo.
        :type route: str
        :param client: Nombre del cliente (nunca su clave), para log y trazas.
        :type client: str or None
        :return: Respuesta, pasos, herramientas, tokens y costo.
        :rtype: AgentResult
        """
        window = self._window(history)
        result = self._tracer.call(
            "agent_run", "chain", self._loop, request_id, question, window, request_id,
            model_name, client, client=client,
        )
        result.model = model_name or ""
        result.route = route
        self._emit(
            "agent_run",
            request_id,
            client=client,
            question_chars=len(question),
            history_messages=len(history or []),
            steps=result.steps,
            tools=result.tools_used,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            stopped=result.stopped,
            model=result.model,
            route=result.route,
            cached_calls=result.cached_calls,
            cost_usd=result.cost_usd,
        )
        return result

    def _window(self, history: Optional[list]) -> list:
        """Recorta el historial a los últimos ``history_window`` mensajes.

        :param history: Mensajes previos.
        :type history: list[dict] or None
        :return: Los mensajes que se mandan al modelo.
        :rtype: list
        """
        messages = list(history or [])
        window = self._history_window
        if window is None or window >= MAX_HISTORY_ITEMS:
            return messages
        return messages[-window:]

    def _emit(self, event: str, request_id: Optional[str], **fields) -> None:
        """Registra un evento si hay registrador.

        :param event: Nombre del evento.
        :param request_id: Id de la petición.
        :param fields: Campos del evento.
        """
        if self._events is not None:
            self._events.emit(event, request_id or "-", **fields)

    def _loop(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        question: str,
        history: list,
        request_id,
        model_name: Optional[str],
        client: Optional[str] = None,
    ) -> AgentResult:
        """Bucle acotado del agente.

        :param question: Pregunta de la persona.
        :param history: Mensajes previos, ya recortados por la ventana.
        :param request_id: Id de la petición.
        :param model_name: Modelo elegido por el enrutador.
        :param client: Nombre del cliente.
        :return: Resultado de la corrida.
        :rtype: AgentResult
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(dict(m) for m in history)
        messages.append({"role": "user", "content": question})
        result = AgentResult(answer=CAP_MESSAGE, steps=0, stopped=True)
        for _ in range(self._max_steps):
            result.steps += 1
            completion = self._tracer.call(
                "model_call", "llm", self._model.complete, request_id, messages,
                model_name, client=client,
            )
            self._account(result, completion, model_name)
            reply = str(completion)
            answer, feedback = self._handle(reply, result, request_id, client)
            if answer is not None:
                result.answer = answer
                result.stopped = False
                return result
            messages.append({"role": "assistant", "content": reply})
            messages.append(
                {"role": "user", "content": f"{TOOL_RESULT_PREFIX} {feedback}"}
            )
        return result

    def _account(self, result: AgentResult, completion, model_name) -> None:
        """Suma tokens, costo y llamadas cacheadas de una llamada al modelo.

        :param result: Resultado en curso.
        :param completion: Respuesta del modelo con sus tokens.
        :param model_name: Modelo usado, para buscar su precio.
        """
        result.input_tokens += completion.input_tokens
        result.output_tokens += completion.output_tokens
        if completion.cached:
            result.cached_calls += 1
        if self._prices is not None and model_name:
            result.cost_usd += self._prices.cost_usd(
                model_name,
                completion.input_tokens,
                completion.output_tokens,
                completion.cached,
            )

    def _handle(self, reply: str, result: AgentResult, request_id, client=None):
        """Interpreta la respuesta del modelo.

        :param reply: Texto JSON del modelo.
        :param result: Resultado en curso (se anotan las herramientas).
        :param request_id: Id de la petición.
        :param client: Nombre del cliente.
        :return: ``(respuesta, None)`` si terminó o ``(None, texto)`` si no.
        """
        try:
            # Solo el primer objeto JSON: algunos modelos pegan varias llamadas
            # en un mensaje; se ejecuta la primera y el modelo pide la siguiente.
            payload, _end = json.JSONDecoder().raw_decode(reply.lstrip())
        except (AttributeError, TypeError, ValueError):
            return None, "error: la respuesta del modelo no es JSON válido"
        if not isinstance(payload, dict):
            return None, "error: la respuesta del modelo no es un objeto JSON"
        if "answer" in payload:
            return str(payload["answer"]), None
        name, args = payload.get("tool"), payload.get("args")
        feedback = self._tracer.call(
            f"tool:{name}", "tool", self._run_tool, request_id, name, args, result,
            request_id, client, client=client,
        )
        return None, feedback

    def _run_tool(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self, name, args, result: AgentResult, request_id, client=None
    ) -> str:
        """Ejecuta una herramienta y devuelve su resultado como texto.

        :param name: Nombre de la herramienta.
        :param args: Argumentos pedidos por el modelo.
        :param result: Resultado en curso.
        :param request_id: Id de la petición, para el evento ``audit``.
        :param client: Nombre del cliente, para el evento ``audit``.
        :return: Texto con el resultado o con el error.
        :rtype: str
        """
        args = args if isinstance(args, dict) else {}
        try:
            if name == "get_product":
                found = self._catalog.get_product(args["product_id"])
                output = found if found is not None else "producto no encontrado"
            elif name == "search_by_category":
                output = self._catalog.search_by_category(args["category"])
            else:
                return f"error: herramienta desconocida {name!r}"
        except KeyError as error:
            return f"error: falta el argumento {error}"
        result.tools_used.append(name)
        key = AUDITED_ARGS[name]
        self._emit(
            "audit",
            request_id,
            client=client,
            action="tool_call",
            tool=name,
            args={key: args[key]},
        )
        return json.dumps(output, ensure_ascii=False)
