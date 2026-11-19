"""API web sin estado del Catálogo de Productos."""

import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from app import compliance, pii
from app.agent import Agent
from app.auth import require_api_key
from app.config import MAX_HISTORY_ITEMS, Config, load_config
from app.catalog import Catalog
from app.events import EventLogger, system_wall_clock
from app.gateway import GatewayModel
from app.llm import FakeModel, ModelUnavailable
from app.metrics import Metrics
from app.output import SAFE_ANSWER, rejection_reason
from app.pricing import PriceTable
from app.ratelimit import RateLimiter
from app.router import choose_model
from app.tracing import Tracer

REQUEST_ID_HEADER = "X-Request-ID"
VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_HISTORY_CONTENT_CHARS = 10000
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class HistoryMessage(BaseModel):
    """Mensaje previo de la conversación que manda el cliente."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_HISTORY_CONTENT_CHARS)


def _resolve_request_id(received: Optional[str]) -> str:
    """Usa el id del cliente si es seguro; si no, genera un UUID.

    :param received: Valor del encabezado ``X-Request-ID``, si llegó.
    :type received: str or None
    :return: El id de la petición.
    :rtype: str
    """
    if received and VALID_REQUEST_ID.fullmatch(received):
        return received
    return str(uuid.uuid4())


def _build_ask_request(max_chars: int):
    """Crea el modelo del cuerpo de ``/ask`` con el largo máximo configurado.

    :param max_chars: Largo máximo de la pregunta.
    :type max_chars: int
    :return: Clase pydantic del cuerpo.
    """

    class AskRequest(BaseModel):
        """Cuerpo de ``POST /ask``."""

        question: str = Field(min_length=1, max_length=max_chars)
        history: Optional[List[HistoryMessage]] = Field(
            default=None, max_length=MAX_HISTORY_ITEMS
        )

        @field_validator("question")
        @classmethod
        def not_blank(cls, value: str) -> str:
            """Rechaza preguntas con solo espacios."""
            if not value.strip():
                raise ValueError("question must not be blank")
            return value

    return AskRequest


def _screen_input(question, history, config: Config, events, request: Request):
    """Enmascara datos personales de la pregunta y el historial.

    Registra un evento ``audit`` con los tipos encontrados, nunca los valores.

    :param question: Pregunta de la persona.
    :param history: Mensajes previos como diccionarios.
    :param config: Configuración con ``pii_mode``.
    :param events: Registrador de eventos.
    :param request: Petición en curso (id y cliente).
    :return: ``(pregunta, historial, bloqueada)``; bloqueada es ``True`` si
        hay datos personales y el modo es ``block``.
    :rtype: tuple
    """
    question, found = pii.redact(question)
    for message in history:
        message["content"], types = pii.redact(message["content"])
        found += types
    if found:
        events.emit(
            "audit", request.state.request_id, client=request.state.client,
            action="pii_detected", stage="input", types=sorted(set(found)),
            mode=config.pii_mode,
        )
    return question, history, bool(found) and config.pii_mode == "block"


def _checked_answer(answer, config: Config, events: EventLogger, request: Request):
    """Valida la respuesta del modelo y enmascara datos personales.

    Si la respuesta no sirve (vacía, muy larga o con datos personales en modo
    ``block``) se entrega ``SAFE_ANSWER`` y se registra el motivo, nunca el texto.

    :param answer: Texto del agente.
    :param config: Configuración con ``pii_mode`` y ``max_answer_chars``.
    :param events: Registrador de eventos.
    :param request: Petición en curso (id y cliente).
    :return: La respuesta que se entrega a la persona.
    :rtype: str
    """
    request_id, client = request.state.request_id, request.state.client
    reason = rejection_reason(answer, config.max_answer_chars)
    if reason:
        events.emit("output_rejected", request_id, client=client, reason=reason)
        return SAFE_ANSWER
    masked, types = pii.redact(answer)
    if not types:
        return answer
    events.emit(
        "audit", request_id, client=client, action="pii_detected",
        stage="output", types=sorted(types), mode=config.pii_mode,
    )
    if config.pii_mode == "block":
        events.emit("output_rejected", request_id, client=client, reason="pii")
        return SAFE_ANSWER
    return masked


def create_app(  # pylint: disable=too-many-locals
    config: Optional[Config] = None,
    model=None,
    catalog=None,
    clock: Callable[[], float] = time.perf_counter,
    wall_clock: Callable[[], datetime] = system_wall_clock,
) -> FastAPI:
    """Construye la aplicación con sus dependencias inyectadas.

    :param config: Configuración; si falta se lee del entorno.
    :type config: Config or None
    :param model: Modelo con ``complete(messages)``; por omisión el simulado.
    :param catalog: Catálogo de productos; por omisión el de la config.
    :param clock: Reloj en segundos para medir la latencia (inyectable).
    :type clock: Callable[[], float]
    :param wall_clock: Reloj de pared con zona horaria, para el campo ``ts``.
    :type wall_clock: Callable[[], datetime]
    :return: La aplicación FastAPI.
    :rtype: FastAPI
    """
    config = config or load_config(os.environ)
    broken_rules = compliance.check(config)
    if broken_rules:
        raise ValueError("production compliance failed: " + "; ".join(broken_rules))
    catalog = catalog or Catalog(config.products_path)
    if model is None:
        if config.model_provider == "gateway":
            model = GatewayModel(config)
        else:
            model = FakeModel(catalog)
    events = EventLogger(config.service_name, wall_clock)
    agent = Agent(
        model=model,
        catalog=catalog,
        max_steps=config.agent_max_steps,
        events=events,
        tracer=Tracer.from_config(config, os.environ),
        prices=PriceTable(config.prices_path),
        history_window=config.history_window,
    )
    ask_request = _build_ask_request(config.max_question_chars)
    metrics = Metrics(config.slo_p95_ms)
    limiter = RateLimiter(config.rate_limit_per_minute, clock)
    authenticate = require_api_key(config.api_keys)
    application = FastAPI(title="Catálogo de Productos")

    def guard(request: Request) -> None:
        """Autentica y después aplica el límite; el orden importa.

        Una clave inválida da ``401`` y no gasta cupo del cliente.
        """
        authenticate(request)
        wait = limiter.check(request.state.client)
        if wait:
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(wait)},
            )

    @application.middleware("http")
    async def trace(request: Request, call_next):
        """Asigna el id de la petición, mide su duración y lo deja en el log.

        Si algo truena responde ``500`` con el id. No se registra el contenido
        de la pregunta ni de la respuesta.
        """
        request_id = _resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started = clock()
        try:
            response = await call_next(request)
        except Exception as error:  # pylint: disable=broad-exception-caught
            events.emit("error", request_id, error_type=type(error).__name__)
            response = JSONResponse(
                {"detail": "internal error", "request_id": request_id},
                status_code=500,
            )
        elapsed_ms = (clock() - started) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        metrics.record_request(elapsed_ms, failed=response.status_code >= 500)
        events.emit(
            "request",
            request_id,
            method=request.method,
            path=request.url.path,
            client=getattr(request.state, "client", "-"),
            status=response.status_code,
            latency_ms=round(elapsed_ms, 3),
        )
        return response

    @application.get("/metrics", dependencies=[Depends(guard)])
    def get_metrics():
        """Peticiones, latencia p50 y p95, tokens y veredicto del SLO."""
        return metrics.snapshot()

    @application.get("/", include_in_schema=False)
    def home():
        """Sirve la página web."""
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    @application.get("/health")
    def health():
        """Estado del proceso."""
        return {"status": "ok", "pid": os.getpid()}

    @application.post("/ask", dependencies=[Depends(guard)])
    def ask(body: ask_request, request: Request):  # type: ignore[valid-type]
        """Responde una pregunta; no guarda nada entre peticiones."""
        request_id = request.state.request_id
        history = [m.model_dump() for m in body.history or []]
        question, history, blocked = _screen_input(
            body.question, history, config, events, request
        )
        if blocked:
            return JSONResponse(
                {"detail": "sensitive data detected", "request_id": request_id},
                status_code=422,
            )
        chosen, route = choose_model(question, config)
        try:
            result = agent.run(
                question,
                history,
                request_id,
                chosen,
                route,
                client=request.state.client,
            )
        except ModelUnavailable as error:
            fields = {"error_type": type(error).__name__}
            if error.status_code is not None:
                fields["upstream_status"] = error.status_code
            events.emit("error", request_id, client=request.state.client, **fields)
            return JSONResponse(
                {"detail": "model unavailable", "request_id": request_id},
                status_code=502,
            )
        metrics.record_tokens(result.input_tokens, result.output_tokens)
        metrics.record_cost(result.cost_usd)
        answer = _checked_answer(result.answer, config, events, request)
        return {
            "request_id": request_id,
            "answer": answer,
            "steps": result.steps,
            "tools_used": result.tools_used,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "model": result.model,
            "route": result.route,
            "cached_calls": result.cached_calls,
            "cost_usd": result.cost_usd,
        }

    return application


def load_env_file(path: Path = ENV_PATH) -> bool:
    """Carga un archivo ``.env`` sin pisar variables ya exportadas.

    Solo es para el punto de entrada de producción. Si el archivo no existe
    no pasa nada. Las pruebas no lo usan: ``create_app`` nunca lee el archivo.

    :param path: Ruta del archivo ``.env``.
    :type path: pathlib.Path
    :return: ``True`` si el archivo existía y se cargó.
    :rtype: bool
    """
    if not path.is_file():
        return False
    return load_dotenv(path, override=False)


# Punto de entrada de uvicorn (``app.main:app``). Con CATALOG_SKIP_DOTENV=1 (solo
# para pruebas) no se lee el .env, para no depender de un archivo real.
if os.environ.get("CATALOG_SKIP_DOTENV") != "1":
    load_env_file()
app = create_app()
