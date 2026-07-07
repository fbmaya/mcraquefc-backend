FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Roda as migrations dentro da VPC (o container alcança o Cloud SQL privado)
# antes de subir a API. exec faz o uvicorn virar PID 1 (recebe SIGTERM do Cloud Run).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
