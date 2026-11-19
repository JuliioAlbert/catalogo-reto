# Catálogo de Productos

API web sin estado que responde preguntas sobre productos y categorías.
Un agente con bucle acotado consulta un catálogo de solo lectura
(`data/products.json`) mediante un modelo simulado y determinista.

## Cómo correrlo

```
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Abre `http://localhost:8000/`. Pruebas, desde `product/`: `pytest`.

## Acceso, límite y producción

- `POST /ask` y `GET /metrics` exigen el encabezado `X-API-Key`. Sin clave o con
  una inválida responden `401 {"detail": "invalid or missing API key"}`. `GET /`,
  `GET /health` y `/docs` no piden clave.
- `API_KEYS` tiene la forma `cliente:clave,cliente2:clave2`. Si está mal formada
  el producto no arranca; el error dice qué entrada falla y su largo, nunca su
  valor. El nombre del cliente va en el log (`client`), en la auditoría y en los
  metadatos de la traza; la clave nunca se escribe, y se compara con
  `hmac.compare_digest`.
- Más de `RATE_LIMIT_PER_MINUTE` peticiones de un cliente en 60 segundos dan
  `429 {"detail": "rate limit exceeded"}` con `Retry-After`. La clave inválida
  se rechaza antes y no gasta cupo. El límite vive en la memoria de cada
  proceso: con varias copias se multiplica (ADR 0011). Es aceptable con una
  sola copia, como en el plan free de Render.
- Con `ENVIRONMENT=production` el producto se niega a arrancar si
  `MODEL_PROVIDER` es `fake`, si `API_KEYS` está vacía o tiene una clave de menos
  de 16 caracteres, o si las trazas están encendidas y `HIDE_INPUTS` o
  `HIDE_OUTPUTS` no valen `true`. Ver `doc/compliance-checklist.md`.
- La página tiene un campo de clave (tipo contraseña). La guarda en
  `sessionStorage` (se pierde al cerrar la pestaña) y la manda en `X-API-Key`.
  Con `401` muestra «Clave inválida»; con `429`, «Demasiadas preguntas; espera N
  segundos».

## Rutas

- `GET /`: página web.
- `GET /health`: `{status, pid}`.
- `GET /products?category=&status=&in_stock=`: `{products, categories}` con filtros opcionales; exige
  `X-API-Key`, no usa el modelo (ADR 0015).
- `POST /ask`: `{question, history?}` devuelve `{request_id, answer, steps,
  tools_used, input_tokens, output_tokens, model, route, cached_calls,
  cost_usd}`. Si el gateway falla responde `502 {"detail": "model
  unavailable", "request_id": ...}`.
- `GET /metrics`: `{pid, requests, error_rate, latency_ms: {p50, p95},
  tokens: {input, output}, cost_usd, slo: {p95_ms_target, met}}`. `met` es
  verdadero si el p95 es menor que `SLO_P95_MS`.

## Costos

Cuatro palancas, cada una medible con el modelo simulado y sin red:

1. Enrutamiento: `MODEL_LARGE` si `ROUTING=false`, si la pregunta pasa de
   `ROUTER_MAX_CHARS` o si contiene «compara», «resume», «explica», «por qué»,
   «analiza» o «todos» (por subcadena, sin distinguir mayúsculas); si no,
   `MODEL_SMALL`.
2. Ventana de historial: solo los últimos `HISTORY_WINDOW` mensajes.
3. Tope de salida: `MODEL_MAX_TOKENS` en cada llamada.
4. Caché de AI Gateway: con `CACHE_TTL_SECONDS` mayor que 0 se manda
   `cf-aig-cache-ttl`; una respuesta `cf-aig-cache-status: HIT` no cuesta.

El costo sale de `data/model_prices.json` (USD por millón de tokens). El modelo
simulado cuenta palabras como tokens: sirve para comparar, no para facturar.
Copia `.env.example` a `.env` y llena los valores de Cloudflare solo en tu
entorno; nunca los subas al repositorio. Ya no hace falta `source`: al
arrancar con `uvicorn app.main:app` se carga `product/.env` solo (con
`python-dotenv`). Una variable ya exportada en la terminal tiene prioridad, y
si no hay `.env` no pasa nada. Las pruebas nunca leen ese archivo: se
protegen con `CATALOG_SKIP_DOTENV=1` (solo para pruebas; no la uses en producción).
Al gateway se manda el token en `Authorization` y en `cf-aig-authorization`
(ambos `Bearer`); nunca se registra ni aparece en los errores.

Prompt de sistema: con cualquier modelo, el primer mensaje que recibe es un
mensaje `system` en español. Explica que se responde solo con un objeto JSON,
las herramientas `get_product` (`product_id`, por ejemplo `PRD-0001`) y
`search_by_category` (`category`) con un ejemplo de cada una, y que al
tener la información se responde `{"answer": "..."}`. No lleva datos de
productos, no cuenta contra `HISTORY_WINDOW` ni lo recorta la ventana. Agrega
los mismos tokens de entrada a la línea base y a las palancas.

## Observabilidad

- Cada respuesta lleva el encabezado `X-Request-ID`; si el cliente lo manda
  (hasta 64 caracteres entre letras, números, `.`, `_` y `-`), se conserva, y si
  no, se genera un UUID. `/ask` también lo devuelve en el cuerpo y la página web
  lo muestra.
- El log va a la salida estándar, una línea JSON por evento, con `ts` (ISO 8601
  UTC), `service`, `event` y `request_id`. Eventos: `request`, `agent_run`,
  `audit` (una por herramienta), y `error` (el tipo de error y, si el gateway respondió un error HTTP,
  `upstream_status` con el código; con tiempo agotado o JSON malformado no
  aparece). Nunca se
  registran preguntas, respuestas ni claves.
- Un fallo interno responde `500` con `{"detail": "internal error",
  "request_id": ...}`.
- Las métricas viven en memoria de cada proceso y se reinician con él. Los
  relojes se inyectan: `create_app(clock=..., wall_clock=...)`.
- Trazas opcionales en LangSmith con `LANGSMITH_TRACING=true` y
  `LANGSMITH_API_KEY` (la clave solo se lee del entorno). Sin la clave el
  servicio funciona igual y no se conecta.

## Variables de entorno

| Variable | Por omisión | Descripción |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Con `production` se aplican las reglas de compliance. |
| `API_KEYS` | vacía | Clientes y claves `cliente:clave,...`; secreto, solo del entorno. |
| `RATE_LIMIT_PER_MINUTE` | `30` | Peticiones por cliente por minuto (>= 1). |
| `MODEL_PROVIDER` | `fake` | Modelo a usar: `fake` o `gateway`. |
| `CF_ACCOUNT_ID` | vacía | Cuenta de Cloudflare (obligatoria con `gateway`). |
| `CF_GATEWAY_ID` | `default` | Gateway de AI Gateway (obligatoria con `gateway`). |
| `CF_API_TOKEN` | vacía | Token de Cloudflare; secreto, solo del entorno. |
| `MODEL_SMALL` | `@cf/meta/llama-3.1-8b-instruct-fast` | Modelo barato. |
| `MODEL_LARGE` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | Modelo capaz. |
| `ROUTING` | `true` | Enrutamiento por pregunta (`true` o `false`). |
| `ROUTER_MAX_CHARS` | `80` | Preguntas más largas van al modelo capaz. |
| `HISTORY_WINDOW` | `6` | Mensajes de historial que se mandan (>= 1; 50 o más: todos). |
| `MODEL_MAX_TOKENS` | `300` | Tope de tokens de salida (>= 1). |
| `MODEL_TEMPERATURE` | `0` | Temperatura; con 0 las evaluaciones se repiten. |
| `CACHE_TTL_SECONDS` | `0` | Caché del gateway en segundos (0: apagada). |
| `PRICES_PATH` | `data/model_prices.json` | Precios por modelo. |
| `AGENT_MAX_STEPS` | `3` | Tope de vueltas del agente (>= 1). |
| `MAX_QUESTION_CHARS` | `2000` | Largo máximo de la pregunta (>= 1). |
| `PRODUCTS_PATH` | `data/products.json` | Archivo de productos. |
| `SLO_P95_MS` | `2000` | Objetivo de latencia p95 en milisegundos (>= 1). |
| `SERVICE_NAME` | `product-catalog` | Campo `service` del log. |
| `LANGSMITH_TRACING` | `false` | Enciende las trazas (`true` o `false`). |
| `LANGSMITH_API_KEY` | sin valor | Clave de LangSmith; solo del entorno. |
| `HIDE_INPUTS` | `true` | No mandar a LangSmith las preguntas. |
| `HIDE_OUTPUTS` | `true` | No mandar a LangSmith las respuestas. |
| `CATALOG_SKIP_DOTENV` | sin valor | Con `1` no se lee `.env` al arrancar; solo pruebas. |
