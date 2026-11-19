# 0005. Trazas opcionales en LangSmith

## Contexto
Las trazas muestran cada corrida, llamada al modelo y herramienta, pero mandan datos a un tercero
y no deben ser obligatorias.

## Decisión
`tracing.py` aplica `@traceable` solo con `LANGSMITH_TRACING=true` y `LANGSMITH_API_KEY` presente.
Si no, las funciones quedan sin envolver y no hay conexión. El `request_id` va en los metadatos.
`HIDE_INPUTS` y `HIDE_OUTPUTS` valen `true` por omisión. La clave solo se lee del entorno.

## Consecuencias
- El producto funciona igual sin clave, red ni la librería activa.
- Para ver textos en las trazas hay que desactivar `HIDE_*` de forma explícita.
- Un fallo de LangSmith no debe romper la respuesta: los errores de trazas se capturan.
