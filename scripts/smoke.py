"""Prueba de humo contra un despliegue: python scripts/smoke.py <url>.

La clave se lee de la variable SMOKE_API_KEY, nunca de un argumento, y nunca se imprime.
"""

import os
import sys

import httpx

QUESTION = {"question": "Cuantos productos hay en ventas?"}


def _report(ok, label):
    """Imprime [OK] o [FAIL] para una comprobacion y devuelve ``ok``."""
    print(f"[{'OK' if ok else 'FAIL'}] {label}")
    return ok


def _status(call):
    """Devuelve el codigo HTTP, o None si la peticion falla por red."""
    try:
        return call().status_code
    except httpx.HTTPError:
        return None


def smoke(url, api_key, client):
    """Corre las tres comprobaciones; True si todas pasan."""
    base = url.rstrip("/")
    results = [
        _report(
            _status(lambda: client.get(f"{base}/health")) == 200,
            "/health responde 200",
        ),
        _report(
            _status(lambda: client.post(f"{base}/ask", json=QUESTION)) == 401,
            "/ask sin clave responde 401",
        ),
        _report(
            _status(
                lambda: client.post(
                    f"{base}/ask", json=QUESTION, headers={"X-API-Key": api_key}
                )
            )
            == 200,
            "/ask con clave responde 200",
        ),
    ]
    return all(results)


def main(argv):
    """Punto de entrada: devuelve 0 si todo pasa, 1 si algo falla, 2 si falta algo."""
    if len(argv) != 2:
        print("Uso: SMOKE_API_KEY=... python scripts/smoke.py <url>")
        return 2
    api_key = os.environ.get("SMOKE_API_KEY", "")
    if not api_key:
        print("Falta la variable SMOKE_API_KEY")
        return 2
    with httpx.Client(timeout=60) as client:
        return 0 if smoke(argv[1], api_key, client) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
