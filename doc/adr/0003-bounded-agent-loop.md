# 0003. Bucle del agente con tope

## Contexto
Un modelo puede pedir herramientas sin terminar nunca, con costo y latencia sin límite.

## Decisión
El bucle da como máximo `AGENT_MAX_STEPS` vueltas (por omisión 3, mínimo 1, validado al arrancar).
Si no hay respuesta al llegar al tope, devuelve el mensaje fijo
`No pude completar la respuesta. Intenta con una pregunta más concreta.`

## Consecuencias
- El costo y el tiempo por pregunta tienen un máximo conocido.
- Preguntas que requieren muchas herramientas pueden fallar; se sube el tope por configuración.
- El mensaje del tope es una constante única, comprobada con una prueba exacta.
