FROM python:3.11-slim

WORKDIR /app

# Copiamos requirements desde la carpeta backend del repo
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiamos el código de la app (carpeta backend/app → /app/app)
COPY backend/app /app/app

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]