"""Lectura y validación de la configuración desde variables de entorno."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping

from app.auth import parse_api_keys

PRODUCT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS_PATH = PRODUCT_DIR / "data" / "products.json"
DEFAULT_PRICES_PATH = PRODUCT_DIR / "data" / "model_prices.json"
DEFAULT_GATEWAY_ID = "default"
DEFAULT_MODEL_SMALL = "@cf/meta/llama-3.1-8b-instruct-fast"
DEFAULT_MODEL_LARGE = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
SUPPORTED_PROVIDERS = ("fake", "gateway")
SUPPORTED_ENVIRONMENTS = ("development", "production")
CLOUDFLARE_VARIABLES = ("CF_ACCOUNT_ID", "CF_GATEWAY_ID", "CF_API_TOKEN")
# Con este largo o más, la ventana de historial se apaga (se manda todo).
MAX_HISTORY_ITEMS = 50
PII_MODES = ("redact", "block")


@dataclass(frozen=True)
class Config:  # pylint: disable=too-many-instance-attributes
    """Configuración validada del servicio.

    :param model_provider: Nombre del modelo a usar.
    :param agent_max_steps: Tope de vueltas del bucle del agente.
    :param max_question_chars: Largo máximo de la pregunta.
    :param products_path: Ruta del archivo de productos.
    :param slo_p95_ms: Objetivo de latencia p95 en milisegundos.
    :param service_name: Valor del campo ``service`` del log.
    :param langsmith_tracing: Si se mandan trazas a LangSmith.
    :param hide_inputs: No mandar a LangSmith las entradas.
    :param hide_outputs: No mandar a LangSmith las salidas.
    :param cf_account_id: Cuenta de Cloudflare.
    :param cf_gateway_id: Gateway de Cloudflare AI Gateway.
    :param cf_api_token: Token de Cloudflare (secreto, fuera de ``repr``).
    :param model_small: Modelo barato.
    :param model_large: Modelo capaz.
    :param routing: Si el enrutador elige el modelo por pregunta.
    :param router_max_chars: Preguntas más largas van al modelo capaz.
    :param history_window: Mensajes de historial que se mandan al modelo.
    :param model_max_tokens: Tope de tokens de salida.
    :param model_temperature: Temperatura del modelo.
    :param cache_ttl_seconds: Caché del gateway en segundos (0: apagada).
    :param prices_path: Ruta del archivo de precios por modelo.
    :param environment: ``development`` o ``production`` (aplica compliance).
    :param api_keys: Claves por cliente (secreto, fuera de ``repr``).
    :param rate_limit_per_minute: Peticiones por cliente por minuto.
    :param pii_mode: ``redact`` enmascara datos personales; ``block`` rechaza.
    :param max_answer_chars: Largo máximo de una respuesta del modelo.
    """

    model_provider: str
    agent_max_steps: int
    max_question_chars: int
    products_path: Path
    slo_p95_ms: int = 2000
    service_name: str = "product-catalog"
    langsmith_tracing: bool = False
    hide_inputs: bool = True
    hide_outputs: bool = True
    cf_account_id: str = ""
    cf_gateway_id: str = DEFAULT_GATEWAY_ID
    cf_api_token: str = field(default="", repr=False)
    model_small: str = DEFAULT_MODEL_SMALL
    model_large: str = DEFAULT_MODEL_LARGE
    routing: bool = True
    router_max_chars: int = 80
    history_window: int = 6
    model_max_tokens: int = 300
    model_temperature: float = 0.0
    cache_ttl_seconds: int = 0
    prices_path: Path = DEFAULT_PRICES_PATH
    environment: str = "development"
    api_keys: Dict[str, str] = field(default_factory=dict, repr=False)
    rate_limit_per_minute: int = 30
    pii_mode: str = "redact"
    max_answer_chars: int = 2000


def _non_negative_int(env: Mapping[str, str], name: str, default: int) -> int:
    """Lee un entero mayor o igual que 0 de ``env``.

    :param env: Variables de entorno.
    :type env: Mapping[str, str]
    :param name: Nombre de la variable.
    :type name: str
    :param default: Valor por omisión.
    :type default: int
    :return: El entero leído.
    :rtype: int
    :raises ValueError: Si no es un entero mayor o igual que 0.
    """
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from error
    if value < 0:
        raise ValueError(f"{name} must be at least 0, got {value}")
    return value


def _number(env: Mapping[str, str], name: str, default: float) -> float:
    """Lee un número decimal no negativo de ``env``.

    :param env: Variables de entorno.
    :type env: Mapping[str, str]
    :param name: Nombre de la variable.
    :type name: str
    :param default: Valor por omisión.
    :type default: float
    :return: El número leído.
    :rtype: float
    :raises ValueError: Si no es un número finito mayor o igual que 0.
    """
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a number, got {raw!r}") from error
    if not 0 <= value < float("inf"):
        raise ValueError(f"{name} must be a finite number >= 0, got {raw!r}")
    return value


def _boolean(env: Mapping[str, str], name: str, default: bool) -> bool:
    """Lee un booleano (``true`` o ``false``) de ``env``.

    :param env: Variables de entorno.
    :type env: Mapping[str, str]
    :param name: Nombre de la variable.
    :type name: str
    :param default: Valor por omisión.
    :type default: bool
    :return: El valor leído.
    :rtype: bool
    :raises ValueError: Si no es ``true`` ni ``false``.
    """
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    lowered = raw.strip().lower()
    if lowered not in ("true", "false"):
        raise ValueError(f"{name} must be true or false, got {raw!r}")
    return lowered == "true"


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    """Lee un entero positivo de ``env``.

    :param env: Variables de entorno.
    :type env: Mapping[str, str]
    :param name: Nombre de la variable.
    :type name: str
    :param default: Valor por omisión.
    :type default: int
    :return: El entero leído.
    :rtype: int
    :raises ValueError: Si no es un entero mayor o igual que 1.
    """
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from error
    if value < 1:
        raise ValueError(f"{name} must be at least 1, got {value}")
    return value


def load_config(env: Mapping[str, str]) -> Config:
    """Construye la configuración a partir de variables de entorno.

    :param env: Variables de entorno (por ejemplo ``os.environ``).
    :type env: Mapping[str, str]
    :return: La configuración validada.
    :rtype: Config
    :raises ValueError: Si algún valor es inválido.
    """
    provider = env.get("MODEL_PROVIDER") or "fake"
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"MODEL_PROVIDER must be one of {SUPPORTED_PROVIDERS}, got {provider!r}"
        )
    environment = env.get("ENVIRONMENT") or "development"
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            f"ENVIRONMENT must be one of {SUPPORTED_ENVIRONMENTS}, "
            f"got {environment!r}"
        )
    pii_mode = env.get("PII_MODE") or "redact"
    if pii_mode not in PII_MODES:
        raise ValueError(f"PII_MODE must be one of {', '.join(PII_MODES)}")
    path = env.get("PRODUCTS_PATH") or str(DEFAULT_PRODUCTS_PATH)
    if provider == "gateway":
        # CF_GATEWAY_ID tiene valor por omisión, así que no es obligatoria.
        missing = [
            name
            for name in CLOUDFLARE_VARIABLES
            if name != "CF_GATEWAY_ID" and not env.get(name)
        ]
        if missing:
            raise ValueError(f"MODEL_PROVIDER=gateway needs {', '.join(missing)}")
    return Config(
        model_provider=provider,
        agent_max_steps=_positive_int(env, "AGENT_MAX_STEPS", 3),
        max_question_chars=_positive_int(env, "MAX_QUESTION_CHARS", 2000),
        products_path=Path(path),
        slo_p95_ms=_positive_int(env, "SLO_P95_MS", 2000),
        service_name=env.get("SERVICE_NAME") or "product-catalog",
        langsmith_tracing=_boolean(env, "LANGSMITH_TRACING", False),
        hide_inputs=_boolean(env, "HIDE_INPUTS", True),
        hide_outputs=_boolean(env, "HIDE_OUTPUTS", True),
        cf_account_id=env.get("CF_ACCOUNT_ID") or "",
        cf_gateway_id=env.get("CF_GATEWAY_ID") or DEFAULT_GATEWAY_ID,
        cf_api_token=env.get("CF_API_TOKEN") or "",
        model_small=env.get("MODEL_SMALL") or DEFAULT_MODEL_SMALL,
        model_large=env.get("MODEL_LARGE") or DEFAULT_MODEL_LARGE,
        routing=_boolean(env, "ROUTING", True),
        router_max_chars=_positive_int(env, "ROUTER_MAX_CHARS", 80),
        history_window=_positive_int(env, "HISTORY_WINDOW", 6),
        model_max_tokens=_positive_int(env, "MODEL_MAX_TOKENS", 300),
        model_temperature=_number(env, "MODEL_TEMPERATURE", 0.0),
        cache_ttl_seconds=_non_negative_int(env, "CACHE_TTL_SECONDS", 0),
        prices_path=Path(env.get("PRICES_PATH") or str(DEFAULT_PRICES_PATH)),
        environment=environment,
        api_keys=parse_api_keys(env.get("API_KEYS")),
        rate_limit_per_minute=_positive_int(env, "RATE_LIMIT_PER_MINUTE", 30),
        pii_mode=pii_mode,
        max_answer_chars=_positive_int(env, "MAX_ANSWER_CHARS", 2000),
    )
