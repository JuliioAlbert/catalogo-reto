# 0001. API sin estado

## Contexto
Escalar el servicio debe ser tan simple como correr más copias, sin sesiones compartidas.

## Decisión
La API no guarda nada entre peticiones. El navegador conserva el historial y lo manda en `history`
de cada `POST /ask`. Las dependencias se construyen en `create_app()` y son de solo lectura.

## Consecuencias
- Cualquier copia puede atender cualquier petición; hay que poner un balanceador sin afinidad.
- Cada petición es más grande porque lleva el historial; por eso se limita su tamaño.
- No hay memoria de largo plazo en el servidor; si se necesita, será otra decisión.
