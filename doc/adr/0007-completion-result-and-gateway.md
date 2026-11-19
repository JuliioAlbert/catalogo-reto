# 0007. El modelo devuelve un resultado con tokens y caché

## Contexto

El modelo real (Cloudflare AI Gateway) informa tokens exactos en `usage` y si la respuesta
vino de caché. La interfaz `complete(messages)` solo devolvía texto, y el agente contaba
palabras por su cuenta. El costo por respuesta necesita tokens reales y el estado de la caché.

## Decisión

`complete(messages, model)` devuelve un `Completion` con `text`, `input_tokens`, `output_tokens`
y `cached`. El modelo simulado y `GatewayModel` cumplen la misma interfaz, así que el agente no
sabe cuál usa. Cualquier fallo del gateway se convierte en `ModelUnavailable`, que `main.py`
responde como `502 model unavailable`.

## Consecuencias

- El agente suma tokens y costo desde lo que informa el modelo, no desde su propio conteo.
- Se actualizan los dobles de prueba de las sesiones 1 y 2.
- Cambiar de proveedor sigue sin tocar el agente.
- El token de Cloudflare solo vive en la configuración y nunca se registra.
