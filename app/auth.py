"""Clave de API por cliente: lectura de ``API_KEYS`` y dependencia de FastAPI."""

import hmac
from typing import Callable, Dict, Mapping, Optional

from fastapi import HTTPException, Request

API_KEY_HEADER = "X-API-Key"
UNAUTHORIZED_DETAIL = "invalid or missing API key"


def parse_api_keys(text: Optional[str]) -> Dict[str, str]:
    """Convierte ``cliente:clave,cliente2:clave2`` en un diccionario.

    Se ignoran los espacios alrededor de cada entrada y las entradas vacías.
    La clave puede contener ``:``; el cliente es lo que va antes del primero.
    Los errores nombran la entrada (su posición) y su largo, nunca su valor.

    :param text: Valor de la variable ``API_KEYS``.
    :type text: str or None
    :return: Diccionario ``cliente -> clave``.
    :rtype: dict[str, str]
    :raises ValueError: Si una entrada no tiene la forma ``cliente:clave`` o si
        un cliente se repite.
    """
    keys: Dict[str, str] = {}
    for position, raw in enumerate((text or "").split(","), start=1):
        entry = raw.strip()
        if not entry:
            continue
        client, separator, key = entry.partition(":")
        client, key = client.strip(), key.strip()
        if not separator or not client or not key:
            raise ValueError(
                f"API_KEYS entry {position} is malformed (length {len(entry)}); "
                "expected client:key"
            )
        if client in keys:
            raise ValueError(
                f"API_KEYS entry {position} repeats client {client!r}"
            )
        keys[client] = key
    return keys


def find_client(keys: Mapping[str, str], received: Optional[str]) -> Optional[str]:
    """Busca el cliente dueño de una clave en tiempo constante.

    Recorre todos los clientes sin cortar al primer acierto y compara con
    ``hmac.compare_digest``.

    :param keys: Diccionario ``cliente -> clave``.
    :type keys: Mapping[str, str]
    :param received: Valor del encabezado ``X-API-Key``, si llegó.
    :type received: str or None
    :return: El nombre del cliente o ``None`` si la clave no coincide.
    :rtype: str or None
    """
    if not received:
        return None
    candidate = received.encode("utf-8")
    found = None
    for client, key in keys.items():
        if hmac.compare_digest(candidate, key.encode("utf-8")):
            found = client
    return found


def require_api_key(keys: Mapping[str, str]) -> Callable[[Request], None]:
    """Crea la dependencia que exige ``X-API-Key``.

    Si la clave es válida deja el nombre del cliente en ``request.state.client``.

    :param keys: Diccionario ``cliente -> clave``.
    :type keys: Mapping[str, str]
    :return: Dependencia para ``Depends``.
    :rtype: Callable[[Request], None]
    """

    def dependency(request: Request) -> None:
        """Valida la clave o responde ``401``."""
        client = find_client(keys, request.headers.get(API_KEY_HEADER))
        if client is None:
            raise HTTPException(status_code=401, detail=UNAUTHORIZED_DETAIL)
        request.state.client = client

    return dependency
