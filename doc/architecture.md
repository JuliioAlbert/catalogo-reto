# Arquitectura del Catálogo de Productos

API web sin estado con un solo agente. El agente consulta un catálogo de productos de solo lectura
y usa un modelo detrás de una interfaz. La sesión 2 agrega observabilidad: id por petición,
log JSON, métricas del proceso y trazas opcionales. La sesión 3 agrega el modelo real por
Cloudflare AI Gateway y cuatro palancas de costo: enrutamiento, ventana de historial, tope de
salida y caché; cada respuesta informa su costo. La sesión 4 lo lleva a producción: clave por
cliente, límite de peticiones, reglas de compliance al arrancar, contenedor, CI y Render.

```mermaid
flowchart LR
    U[Personal de ventas] --> W[index.html clave en sessionStorage]
    W -->|POST /ask con X-API-Key| M[main.py create_app]
    M --> C[config.py]
    C --> CP[compliance.py solo en production]
    M -->|X-API-Key| AU[auth.py cliente]
    AU -->|401| M
    M -->|cliente| RL[ratelimit.py ventana 60 s]
    RL -->|429 Retry-After| M
    M -->|X-Request-ID, client, request, error| E[events.py log JSON]
    M -->|requests, errores, tokens, cost_usd| X[metrics.py]
    M -->|GET /metrics con clave| X
    M -->|pregunta| R[router.py small o large]
    M --> A[agent.py bucle con tope y ventana]
    A -->|agent_run, audit con client| E
    A -->|complete messages, model| L[llm.py interfaz Completion]
    L --> F[Modelo simulado fake]
    L --> G[gateway.py GatewayModel]
    G -->|max_tokens, cf-aig-cache-ttl| CF[(Cloudflare AI Gateway)]
    A -->|tokens, cached| P[pricing.py]
    P --> PJ[(data/model_prices.json)]
    A -->|get_product, search_by_category| D[catalog.py]
    D --> J[(data/products.json)]
    A -.->|metadatos request_id y client| T[tracing.py]
    T -.-> S[(LangSmith opcional)]
    M -->|pregunta, historial, respuesta| PII[pii.py y output.py]
    E --> O[(stdout)]
    A -->|answer, tokens, cost_usd| M
    M -->|model, route, cost_usd, request_id| W
    G -.->|falla 502| M
```

## Publicación

```mermaid
flowchart LR
    P[push o pull request] --> S[style pylint]
    S --> UN[unit y BDD con 80 por ciento]
    UN --> E2E[e2e Playwright con fake]
    E2E --> DK[docker build]
    DK -->|checksPass| R[Render Blueprint docker]
    R -->|/health| H[scripts/smoke.py]
```

## Decisiones

- ADR 0001: API sin estado.
- ADR 0002: modelo detrás de la interfaz `complete(messages)`.
- ADR 0003: bucle del agente con tope de pasos.
- ADR 0004: log JSON por eventos, sin contenido.
- ADR 0005: trazas opcionales en LangSmith.
- ADR 0006: métricas por proceso y relojes inyectados.
- ADR 0007: el modelo devuelve un `Completion` (tokens y caché) y el gateway falla como 502.
- ADR 0008: enrutador de modelo por regla en código.
- ADR 0009: costo calculado con una tabla de precios, también para el simulado.
- ADR 0010: una clave por cliente en `X-API-Key`, nunca registrada.
- ADR 0011: límite de peticiones por cliente en memoria, con reloj inyectado.
- ADR 0012: compliance como comprobación que impide arrancar en producción.
- ADR 0013: datos personales enmascarados o bloqueados en entrada y salida.
- ADR 0014: validación de la respuesta del modelo antes de entregarla.
