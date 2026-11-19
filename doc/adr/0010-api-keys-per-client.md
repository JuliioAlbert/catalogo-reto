# ADR 0010: Una clave por cliente en el encabezado X-API-Key

## Contexto

La spec 04 publica el producto en internet. `POST /ask` cuesta dinero y `GET /metrics` revela
uso, así que hace falta saber quién llama y poder cortar a un cliente sin afectar a los demás.
La clave es un secreto: no puede acabar en el log, en una traza ni en un error.

## Decisión

- `API_KEYS` (`cliente:clave,cliente2:clave2`) se lee y valida al arrancar en `app/auth.py`.
  Una entrada mal formada impide arrancar; el error dice el número de entrada y su largo,
  nunca su valor.
- Una dependencia de FastAPI protege `/ask` y `/metrics`. Compara con `hmac.compare_digest`
  y deja el nombre del cliente en `request.state.client`. `/`, `/health` y `/docs` quedan abiertas.
- Solo el nombre del cliente viaja al log (`client`), a la auditoría y a los metadatos de la traza.
  La clave va en un campo con `repr=False`.

## Consecuencias

- Rotar o revocar una clave es cambiar la variable en Render y reiniciar; no hay base de datos.
- La API sigue sin estado: la autenticación no guarda sesiones.
- Todas las pruebas y la verificación deben mandar la clave; las de la sesión 3 se actualizan.
- Una clave filtrada da acceso total al cliente hasta rotarla: por eso se exigen 16 caracteres
  en producción (ADR 0012).
