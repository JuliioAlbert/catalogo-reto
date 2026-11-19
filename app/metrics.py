"""Métricas en memoria del servicio: peticiones, latencia, tokens y SLO."""

import math
import os
from collections import deque
from threading import Lock
from typing import List

MAX_LATENCY_SAMPLES = 10000


def percentile(values: List[float], fraction: float) -> float:
    """Calcula un percentil por el método del rango más cercano.

    :param values: Muestras ya recolectadas.
    :type values: list[float]
    :param fraction: Fracción entre 0 y 1 (0.95 es el percentil 95).
    :type fraction: float
    :return: El percentil, o 0 si no hay muestras.
    :rtype: float
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


class Metrics:  # pylint: disable=too-many-instance-attributes
    """Acumula métricas del proceso; no guarda preguntas ni respuestas.

    :param slo_p95_ms: Objetivo de latencia p95 en milisegundos.
    :type slo_p95_ms: float
    """

    def __init__(self, slo_p95_ms: float):
        self._slo_p95_ms = slo_p95_ms
        self._latencies: deque = deque(maxlen=MAX_LATENCY_SAMPLES)
        self._requests = 0
        self._errors = 0
        self._input_tokens = 0
        self._output_tokens = 0
        self._cost_usd = 0.0
        self._lock = Lock()

    def record_request(self, latency_ms: float, failed: bool = False) -> None:
        """Registra una petición.

        :param latency_ms: Duración de la petición en milisegundos.
        :type latency_ms: float
        :param failed: Si la petición terminó en error del servidor.
        :type failed: bool
        """
        with self._lock:
            self._requests += 1
            self._latencies.append(latency_ms)
            if failed:
                self._errors += 1

    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Suma los tokens de una respuesta.

        :param input_tokens: Tokens de entrada.
        :type input_tokens: int
        :param output_tokens: Tokens de salida.
        :type output_tokens: int
        """
        with self._lock:
            self._input_tokens += input_tokens
            self._output_tokens += output_tokens

    def record_cost(self, cost_usd: float) -> None:
        """Suma el costo de una respuesta.

        :param cost_usd: Costo en USD.
        :type cost_usd: float
        """
        with self._lock:
            self._cost_usd += cost_usd

    def snapshot(self) -> dict:
        """Devuelve el estado actual de las métricas.

        :return: Proceso, peticiones, tasa de error, latencias, tokens, costo y SLO.
        :rtype: dict
        """
        with self._lock:
            samples = list(self._latencies)
            p50 = percentile(samples, 0.50)
            p95 = percentile(samples, 0.95)
            rate = self._errors / self._requests if self._requests else 0.0
            return {
                "pid": os.getpid(),
                "requests": self._requests,
                "error_rate": rate,
                "latency_ms": {"p50": p50, "p95": p95},
                "tokens": {"input": self._input_tokens, "output": self._output_tokens},
                "cost_usd": self._cost_usd,
                "slo": {
                    "p95_ms_target": self._slo_p95_ms,
                    "met": p95 < self._slo_p95_ms,
                },
            }
