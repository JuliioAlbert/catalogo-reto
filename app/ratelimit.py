"""Límite de peticiones por cliente con ventana deslizante y reloj inyectado."""

import math
from collections import deque
from typing import Callable, Deque, Dict

WINDOW_SECONDS = 60.0


class RateLimiter:
    """Cuenta las peticiones de cada cliente en los últimos 60 segundos.

    Vive en memoria de cada proceso (ver ADR 0011).

    :param limit: Peticiones permitidas por ventana.
    :type limit: int
    :param clock: Reloj en segundos (inyectable).
    :type clock: Callable[[], float]
    """

    def __init__(self, limit: int, clock: Callable[[], float]) -> None:
        self._limit = limit
        self._clock = clock
        self._hits: Dict[str, Deque[float]] = {}

    def check(self, client: str) -> int:
        """Registra una petición del cliente si cabe en el límite.

        Una petición rechazada no se cuenta.

        :param client: Nombre del cliente.
        :type client: str
        :return: ``0`` si pasa; si no, los segundos de ``Retry-After``.
        :rtype: int
        """
        now = self._clock()
        self._forget_inactive(now)
        hits = self._hits.setdefault(client, deque())
        if len(hits) < self._limit:
            hits.append(now)
            return 0
        wait = hits[0] + WINDOW_SECONDS - now
        return max(1, math.ceil(wait))

    def _forget_inactive(self, now: float) -> None:
        """Quita las marcas vencidas y los clientes sin actividad.

        :param now: Hora actual del reloj.
        :type now: float
        """
        for name in list(self._hits):
            hits = self._hits[name]
            while hits and now - hits[0] >= WINDOW_SECONDS:
                hits.popleft()
            if not hits:
                del self._hits[name]
