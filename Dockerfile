# Imagen del Catálogo de Productos: Python 3.12 delgado y un usuario sin privilegios.
FROM python:3.12-slim

# No escribir .pyc ni guardar la salida en buffer (los logs salen de inmediato).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

# Usuario que no es root.
RUN useradd --create-home --uid 10001 appuser

# Primero las dependencias, para aprovechar la caché de capas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo el código y los datos; lo demás lo deja fuera .dockerignore.
COPY app ./app
COPY data ./data

USER appuser

# Render define PORT; en local se usa 8000.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
