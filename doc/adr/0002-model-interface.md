# 0002. El modelo detrás de una interfaz

## Contexto
Hoy solo existe un modelo simulado, pero más adelante se querrá un modelo real sin reescribir el agente.

## Decisión
El agente depende solo de `complete(messages)`, que devuelve un único objeto JSON (`tool` o `answer`).
`MODEL_PROVIDER` elige la implementación; ahora solo `fake`, determinista y sin red.

## Consecuencias
- Las pruebas son deterministas, rápidas y sin costo.
- Cambiar de modelo implica agregar una clase y un valor de `MODEL_PROVIDER`.
- El agente debe tolerar salidas inválidas de un modelo real (JSON roto, herramienta desconocida).
