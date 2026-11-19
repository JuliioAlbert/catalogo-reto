# ADR 0014: Validación de la respuesta del modelo

## Contexto

El modelo puede responder vacío, demasiado largo o con datos personales. La API no debe entregar
eso tal cual.

## Decisión

- `app/output.py`, `rejection_reason(respuesta, máximo)`, rechaza una respuesta que no es texto,
  está vacía o pasa de `MAX_ANSWER_CHARS` (2000 por omisión).
- Una respuesta rechazada se cambia por `SAFE_ANSWER` y se registra el evento `output_rejected`
  con el motivo (`empty`, `too_long`, `not_text`, `pii`), nunca el texto.
- La validación corre en `main.py` después del agente y antes de la respuesta HTTP.

## Consecuencias

- La persona siempre recibe un texto útil o un aviso claro, nunca vacío.
- Un límite bajo puede reemplazar una respuesta válida: se sube con `MAX_ANSWER_CHARS`.
