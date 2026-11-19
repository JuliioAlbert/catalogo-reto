# ADR 0011: Límite de peticiones por cliente, en memoria y con reloj inyectado

## Contexto

Un cliente con la clave puede gastar el presupuesto del modelo con un ciclo. Hay que limitarlo
por cliente (`RATE_LIMIT_PER_MINUTE`, 30 por omisión) y responder `429` con `Retry-After`.
El producto es de un solo servicio en el plan gratuito de Render y no hay almacén compartido.

## Decisión

- `app/ratelimit.py` guarda, por cliente, las marcas de tiempo de los últimos 60 segundos
  (ventana deslizante). Recibe el reloj por parámetro, como las métricas (ADR 0006).
- Va después de la autenticación: una petición con clave inválida no gasta cupo de nadie.
- Al rechazar devuelve `429 {"detail": "rate limit exceeded"}` y `Retry-After` con los segundos
  que faltan, redondeados hacia arriba (mínimo 1).
- Se descartan los clientes sin marcas vigentes para que la memoria no crezca.

## Consecuencias

- El límite es por copia del proceso: con N copias el cliente puede hacer N veces el límite.
  Es aceptable con una copia; para escalar haría falta un almacén compartido (nuevo ADR).
- Un reinicio borra los contadores.
- Las pruebas avanzan un reloj falso, sin esperas reales.
