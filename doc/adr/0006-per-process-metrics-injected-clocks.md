# 0006. Métricas por proceso y relojes inyectados

## Contexto
La API es sin estado y se escala con más copias; aun así `/metrics` debe dar latencia, errores,
tokens y el veredicto del SLO. Las pruebas deben ser deterministas.

## Decisión
`/metrics` describe solo el proceso que responde (incluye `pid`) y vive en memoria, sin guardar
preguntas ni respuestas. `slo.met` es verdadero si el p95 queda por debajo de `SLO_P95_MS`.
Se inyectan dos relojes: uno monotónico para la latencia y uno de pared para `ts`; no se usa
`datetime.now()` directo.

## Consecuencias
- Agregar métricas entre copias es tarea del recolector externo, no de la API.
- Las métricas se pierden al reiniciar; las latencias se acotan a una ventana.
- Las pruebas fijan los relojes y comprueban valores exactos.
