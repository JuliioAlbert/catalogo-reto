# Lista de compliance de producción

Con `ENVIRONMENT=production` el producto se niega a arrancar si se rompe una de estas reglas
(`app/compliance.py`, llamado desde `create_app`). El error lista todas las reglas rotas y nunca
muestra el valor de una clave.

| Regla | Dónde está en el código | Cómo se comprueba |
| --- | --- | --- |
| `MODEL_PROVIDER` no es `fake` | `app/compliance.py`, `check` | `tests/test_compliance_and_config.py` (regla por regla) y escenario de `tests/features/production.feature` |
| `API_KEYS` no está vacía | `app/compliance.py`, `check` | `tests/test_compliance_and_config.py` y el escenario de arranque en producción |
| Cada clave tiene 16 caracteres o más | `app/compliance.py`, `check` (`MIN_KEY_CHARS`) | `tests/test_compliance_and_config.py` (15 falla, 16 pasa) |
| Con trazas encendidas, `HIDE_INPUTS` y `HIDE_OUTPUTS` valen `true` | `app/compliance.py`, `check` | `tests/test_compliance_and_config.py` (cada variable por separado) |
| `API_KEYS` bien formada (`cliente:clave`); si no, no arranca y el error da la entrada y su largo | `app/auth.py`, `parse_api_keys`; `app/config.py`, `load_config` | `tests/test_auth_and_ratelimit.py` (el mensaje no contiene el valor) |
| `ENVIRONMENT` es `development` o `production` | `app/config.py`, `load_config` | `tests/test_compliance_and_config.py` |
| `/ask` y `/metrics` exigen `X-API-Key` (`401` si falta o es inválida) | `app/auth.py`, `require_api_key`; `app/main.py`, `guard` | `tests/test_api_security.py` y `tests/features/production.feature` |
| Las claves se comparan en tiempo constante | `app/auth.py`, `find_client` (`hmac.compare_digest`) | `tests/test_auth_and_ratelimit.py` y revisión de `qa-style` |
| Límite de peticiones por cliente y por minuto (`429` con `Retry-After`) | `app/ratelimit.py`, `RateLimiter`; `app/main.py`, `guard` | `tests/test_auth_and_ratelimit.py` y `tests/features/production.feature` (reloj falso) |
| La clave nunca va al log, a la traza ni a un error | `app/config.py` (`repr=False`), `app/agent.py` y `app/tracing.py` (solo el nombre del cliente) | `tests/test_api_security.py`, `tests/test_production_steps.py` (busca la clave en el log y en las respuestas) |
| La página guarda la clave solo en `sessionStorage` | `app/static/index.html` | `tests/test_api_security.py` (sin `localStorage` ni clave en la página) |
| Los secretos no están en el repositorio ni en la imagen | `.gitignore` y `.dockerignore` (`.env`); `render.yaml` (`sync: false`) | `tests/test_deployment_files.py` |
| Los datos personales (correo, teléfono, RFC, CURP, tarjeta) se enmascaran o bloquean en pregunta, historial y respuesta | `app/pii.py`; `app/main.py` (`_screen_input`, `_checked_answer`) | `tests/test_pii.py`, `tests/test_output_validation.py` y `tests/features/hardening.feature` |
| `PII_MODE` es `redact` o `block`; otro valor impide arrancar | `app/config.py`, `load_config` | `tests/test_output_validation.py` |
| La respuesta del modelo no se entrega vacía, larga ni con datos personales (`output_rejected`) | `app/output.py`; `app/main.py`, `_checked_answer` | `tests/test_output_validation.py` |
| La auditoría `pii_detected` guarda tipos y cliente, nunca el valor | `app/main.py` | `tests/test_output_validation.py` (busca el valor en el log) |
