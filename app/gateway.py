"""Modelo real: Cloudflare Workers AI a través de AI Gateway."""

from typing import Optional, Sequence

import httpx

from app.llm import Completion, ModelUnavailable

GATEWAY_URL = (
    "https://gateway.ai.cloudflare.com/v1/{account}/{gateway}"
    "/workers-ai/v1/chat/completions"
)
AUTH_HEADER = "cf-aig-authorization"
CACHE_TTL_HEADER = "cf-aig-cache-ttl"
CACHE_STATUS_HEADER = "cf-aig-cache-status"
REQUEST_TIMEOUT_SECONDS = 30.0


class GatewayModel:
    """Cliente del endpoint de chat de AI Gateway, con cliente HTTP inyectable.

    :param config: Configuración con las variables ``cf_*`` y los topes.
    :type config: Config
    :param client: Cliente httpx; por omisión uno con tiempo límite.
    :type client: httpx.Client or None
    """

    def __init__(self, config, client: Optional[httpx.Client] = None) -> None:
        self._config = config
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)
        self._url = GATEWAY_URL.format(
            account=config.cf_account_id, gateway=config.cf_gateway_id
        )

    def complete(
        self, messages: Sequence[dict], model: Optional[str] = None
    ) -> Completion:
        """Llama al modelo y lee texto, tokens y estado del caché.

        :param messages: Conversación como lista de ``{"role", "content"}``.
        :type messages: Sequence[dict]
        :param model: Modelo elegido; por omisión ``model_large``.
        :type model: str or None
        :return: Texto, tokens y si la llamada fue un ``HIT`` del caché.
        :rtype: Completion
        :raises ModelUnavailable: Ante cualquier fallo de red, HTTP o formato.
        """
        config = self._config
        bearer = f"Bearer {config.cf_api_token}"
        headers = {"Authorization": bearer, AUTH_HEADER: bearer}
        if config.cache_ttl_seconds > 0:
            headers[CACHE_TTL_HEADER] = str(config.cache_ttl_seconds)
        body = {
            "model": model or config.model_large,
            "messages": list(messages),
            "max_tokens": config.model_max_tokens,
            "temperature": config.model_temperature,
        }
        try:
            response = self._client.post(self._url, json=body, headers=headers)
            response.raise_for_status()
            return self._parse(response)
        except httpx.HTTPStatusError as error:
            raise ModelUnavailable(
                type(error).__name__, error.response.status_code
            ) from None
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as error:
            # Solo el tipo del error: el mensaje podría incluir datos sensibles.
            raise ModelUnavailable(type(error).__name__) from None

    @staticmethod
    def _parse(response: httpx.Response) -> Completion:
        """Convierte la respuesta HTTP en un ``Completion``.

        :param response: Respuesta en formato OpenAI.
        :return: Texto, tokens y estado del caché.
        :rtype: Completion
        """
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data["usage"]
        status = response.headers.get(CACHE_STATUS_HEADER, "")
        if not isinstance(text, str):
            raise TypeError("content must be text")
        return Completion(
            text,
            int(usage["prompt_tokens"]),
            int(usage["completion_tokens"]),
            status.strip().upper() == "HIT",
        )
