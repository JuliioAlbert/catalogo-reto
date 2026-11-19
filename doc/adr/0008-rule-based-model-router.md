# 0008. Enrutador de modelo por regla en código

## Contexto

Las preguntas simples no necesitan el modelo grande, que cuesta unas siete veces más por token.
Usar otro modelo para decidir sumaría costo, latencia y variabilidad.

## Decisión

`router.py` elige el modelo con una función pura: `MODEL_LARGE` si `ROUTING=false`, si la
pregunta pasa de `ROUTER_MAX_CHARS` o si contiene alguna palabra clave («compara», «resume»,
«explica», «por qué», «analiza», «todos»); si no, `MODEL_SMALL`. Devuelve también el motivo,
que sale en `route`. El modelo elegido se usa en todas las vueltas de la pregunta.

## Consecuencias

- Es determinista, gratis y fácil de probar en sus bordes.
- Puede enviar una pregunta difícil al modelo pequeño; `verification evaluate` mide si la
  calidad baja, y si baja la palanca no se usa.
- `ROUTING=false` da la línea base para comparar costos.
