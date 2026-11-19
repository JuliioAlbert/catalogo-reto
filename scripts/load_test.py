"""Prueba de carga: muchas preguntas concurrentes contra una URL publicada.

Uso: ``SMOKE_API_KEY=<clave> python scripts/load_test.py <url> [total] [concurrencia]``

La clave se lee de la variable ``SMOKE_API_KEY``, nunca de un argumento. Imprime
total, errores, 429, latencias p50 y p95, peticiones por segundo y costo.
"""

import asyncio
import os
import sys
import time

import httpx

QUESTIONS = (
    "¿Quién es PRD-0004?",
    "¿Cuánto cuesta PRD-0002?",
    "Lista la categoría de Electrónica",
    "¿Qué productos hay en Oficina?",
)


def percentile(values: list, fraction: float) -> float:
    """Percentil sencillo (por rango) de una lista de números.

    :param values: Números, en cualquier orden.
    :param fraction: Entre 0 y 1; por ejemplo 0.95.
    :return: El valor en ese percentil; 0 si la lista está vacía.
    :rtype: float
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


async def one_request(client: httpx.AsyncClient, url: str, key: str, number: int):
    """Manda una pregunta y devuelve ``(estado, milisegundos, costo)``.

    :param client: Cliente HTTP asíncrono compartido.
    :param url: URL base del servicio.
    :param key: Clave del cliente.
    :param number: Número de la petición; elige la pregunta.
    :return: Código HTTP (0 si falló la red), latencia en ms y costo en USD.
    :rtype: tuple[int, float, float]
    """
    started = time.perf_counter()
    try:
        response = await client.post(
            f"{url}/ask",
            json={"question": QUESTIONS[number % len(QUESTIONS)]},
            headers={"X-API-Key": key},
        )
    except httpx.HTTPError:
        return 0, (time.perf_counter() - started) * 1000, 0.0
    cost = 0.0
    if response.status_code == 200:
        cost = float(response.json().get("cost_usd", 0.0))
    return response.status_code, (time.perf_counter() - started) * 1000, cost


async def run(url: str, key: str, total: int, concurrency: int, transport=None) -> dict:
    """Lanza ``total`` peticiones, ``concurrency`` a la vez, y resume.

    :param url: URL base del servicio.
    :param key: Clave del cliente.
    :param total: Número de peticiones.
    :param concurrency: Peticiones simultáneas como máximo.
    :param transport: Transporte de httpx (para pruebas).
    :return: Resumen con ``total``, ``ok``, ``rate_limited``, ``errors``,
        ``p50_ms``, ``p95_ms``, ``rps`` y ``cost_usd``.
    :rtype: dict
    """
    gate = asyncio.Semaphore(concurrency)

    async def limited(client, number):
        async with gate:
            return await one_request(client, url, key, number)

    started = time.perf_counter()
    async with httpx.AsyncClient(transport=transport, timeout=30) as client:
        results = await asyncio.gather(*(limited(client, n) for n in range(total)))
    elapsed = time.perf_counter() - started
    latencies = [ms for status, ms, _cost in results if status == 200]
    return {
        "total": total,
        "ok": sum(1 for status, _ms, _cost in results if status == 200),
        "rate_limited": sum(1 for status, _ms, _cost in results if status == 429),
        "errors": sum(1 for status, _ms, _cost in results if status not in (200, 429)),
        "p50_ms": round(percentile(latencies, 0.5), 1),
        "p95_ms": round(percentile(latencies, 0.95), 1),
        "rps": round(total / elapsed, 1) if elapsed else 0.0,
        "cost_usd": round(sum(cost for _status, _ms, cost in results), 6),
    }


def main(args: list) -> int:
    """Corre la prueba; 0 si no hubo errores (los 429 no cuentan como error).

    :param args: ``[url, total?, concurrencia?]``.
    :return: Código de salida.
    :rtype: int
    """
    key = os.environ.get("SMOKE_API_KEY", "")
    if not args or not key:
        print("Uso: SMOKE_API_KEY=<clave> python scripts/load_test.py <url> [N] [C]")
        return 2
    total = int(args[1]) if len(args) > 1 else 50
    concurrency = int(args[2]) if len(args) > 2 else 10
    summary = asyncio.run(run(args[0].rstrip("/"), key, total, concurrency))
    for name, value in summary.items():
        print(f"{name}: {value}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
