# ADR 0013: Detección de datos personales con enmascarado o bloqueo

## Contexto

Una pregunta puede traer correos, teléfonos, RFC, CURP o tarjetas. Si llegan al modelo (un
tercero) o vuelven en la respuesta, se filtran. El log y las trazas ya no guardan texto, pero el
modelo sí lo recibe.

## Decisión

- `app/pii.py` detecta con expresiones regulares correo, teléfono mexicano, RFC, CURP y tarjeta
  (13 a 19 dígitos que pasan Luhn). `redact(texto)` devuelve el texto enmascarado
  (`[CORREO]`, `[TELEFONO]`...) y los tipos encontrados, nunca los valores.
- Se revisa la pregunta y el historial antes de llamar al agente, y la respuesta antes de entregarla.
- `PII_MODE=redact` (por omisión) enmascara y sigue; `PII_MODE=block` responde
  `422 {"detail": "sensitive data detected"}` a la entrada y reemplaza una respuesta con datos
  personales por una respuesta segura. Otro valor impide arrancar.
- Cada hallazgo escribe un evento `audit` con `action=pii_detected`, `stage` (`input` u `output`),
  los tipos y el cliente.

## Consecuencias

- Un id de producto, un precio o un conteo no se marcan: los patrones piden formas completas.
- Las expresiones regulares no cubren nombres propios ni direcciones: es una capa, no la única.
- Enmascarar puede quitar contexto útil; por eso `block` existe para quien prefiere rechazar.
