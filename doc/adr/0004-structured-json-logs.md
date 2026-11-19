# 0004. Log JSON por eventos, sin contenido

## Contexto
Hay que responder "qué pasó con la petición X" con datos. Las preguntas pueden contener datos
personales de productos.

## Decisión
Un `EventLogger` escribe una línea JSON por evento en la salida estándar, con `ts` (UTC, desde un
reloj inyectado), `service`, `event` y `request_id`. Eventos: `request`, `agent_run`, `audit`, `error`.
Nunca se registra el texto de la pregunta ni de la respuesta, solo longitudes, conteos y nombres.
Cada petición lleva un id: el `X-Request-ID` del cliente o un UUID.

## Consecuencias
- Se puede filtrar todo por `request_id`; el log es apto para cualquier recolector.
- Sin el texto no se puede reproducir una conversación desde el log; es intencional.
- Los `args` del evento `audit` solo pueden ser ids o categorías.
- Las pruebas fijan el reloj y comprueban que el texto no aparece.
