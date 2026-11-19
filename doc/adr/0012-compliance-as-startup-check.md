# ADR 0012: Compliance como código que impide arrancar

## Contexto

Las reglas de producción (sin modelo simulado, claves largas, trazas sin contenido) se rompen
por descuido al configurar Render, y nadie lo nota hasta que hay un problema. Una lista de
verificación que se lee a mano no basta.

## Decisión

- `app/compliance.py` expone `check(config)`, que devuelve la lista de reglas rotas.
  Con `ENVIRONMENT=production`, `create_app` la llama al arrancar y, si no está vacía,
  levanta `ValueError` con todos los motivos juntos (sin valores secretos).
- Reglas: `MODEL_PROVIDER` distinto de `fake`; `API_KEYS` no vacía y cada clave de 16
  caracteres o más; con trazas encendidas, `HIDE_INPUTS` y `HIDE_OUTPUTS` en `true`.
- Con `development` (por omisión) no se aplica nada, para no estorbar las pruebas.
- `doc/compliance-checklist.md` relaciona regla, lugar del código y prueba que la comprueba.

## Consecuencias

- Un despliegue mal configurado falla en el arranque y el `healthCheckPath` de Render lo detiene.
- Cada regla nueva exige su fila en la tabla y su prueba.
- Falla pronto y fuerte: es mejor un servicio que no arranca que uno inseguro.
