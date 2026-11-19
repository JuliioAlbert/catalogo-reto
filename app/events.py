"""Registro de eventos en JSON, una línea por evento, en la salida estándar."""

import json
import sys
from datetime import datetime, timezone
from typing import Callable


def system_wall_clock() -> datetime:
    """Reloj de pared por omisión: la hora actual en UTC.

    Es el único punto donde se lee la hora real; el resto del código recibe
    un reloj inyectado.

    :return: Fecha y hora con zona horaria UTC.
    :rtype: datetime
    """
    return datetime.now(timezone.utc)


class EventLogger:
    """Escribe eventos como líneas JSON con ``ts``, ``service`` y ``event``.

    :param service: Nombre del servicio (campo ``service``).
    :type service: str
    :param wall_clock: Reloj inyectado que devuelve un ``datetime`` con zona.
    :type wall_clock: Callable[[], datetime]
    """

    def __init__(
        self,
        service: str,
        wall_clock: Callable[[], datetime] = system_wall_clock,
    ) -> None:
        self._service = service
        self._wall_clock = wall_clock

    def emit(self, event: str, request_id: str, **fields) -> dict:
        """Escribe un evento y lo devuelve.

        :param event: Nombre del evento (``request``, ``agent_run``, ...).
        :type event: str
        :param request_id: Id de la petición.
        :type request_id: str
        :param fields: Campos propios del evento.
        :return: El registro escrito.
        :rtype: dict
        """
        record = {
            "ts": self._wall_clock().astimezone(timezone.utc).isoformat(),
            "service": self._service,
            "event": event,
            "request_id": request_id,
        }
        record.update(fields)
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        return record
