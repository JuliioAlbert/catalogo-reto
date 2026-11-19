# ADR 0015: Endpoint `/products` para la vista del catálogo

## Contexto

La página era solo un chat: para ver un producto había que preguntarle al modelo, con costo y latencia.
Una vista de catálogo necesita listar y filtrar sin pasar por el agente.

## Decisión

- `GET /products` lee directo de `Catalog.list_products` (sin modelo) y devuelve productos y categorías.
- Usa la misma dependencia `guard` que `/ask`: clave por cliente y límite por minuto compartido.
- Los filtros se validan con FastAPI (`status` es un `Literal`, `category` tiene largo máximo).
- Cada consulta deja un evento `audit` con cliente y filtros.

## Consecuencias

- Listar el catálogo cuesta 0 USD y no depende del gateway.
- Cada carga de la página y cada cambio de categoría gasta cupo del límite; con 30 por minuto alcanza para uso normal.
- Los datos del catálogo siguen siendo de solo lectura; no hay endpoints de escritura.
