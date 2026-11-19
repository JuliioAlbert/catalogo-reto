# 0009. Costo calculado con una tabla de precios, también para el simulado

## Contexto

Las palancas de costo solo valen si se miden, y medir con el modelo real gasta cuota y no es
repetible. Los precios cambian y no deben estar en el código.

## Decisión

`pricing.py` lee `data/model_prices.json` (USD por millón de tokens) y calcula el costo de cada
llamada con su modelo; una llamada cacheada (`HIT`) cuesta 0. El modo `fake` tiene dos modelos
simulados con los nombres de `MODEL_SMALL` y `MODEL_LARGE`, así que se calculan con el precio
de su nombre. El costo se suma por respuesta (`cost_usd`) y por proceso (`/metrics`).

## Consecuencias

- Las palancas se evalúan sin red y de forma repetible.
- Los tokens del simulado son palabras: sirven para comparar, no para facturar.
- Al arrancar se valida que ambos modelos tengan precio; si no, el servicio no inicia.
- Actualizar precios es cambiar un archivo, no código.
