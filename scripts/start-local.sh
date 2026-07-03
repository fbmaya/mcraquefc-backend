#!/bin/sh
set -e

echo "→ Aplicando migrations (Alembic)..."
python scripts/migrate.py

echo "→ Rodando seed..."
python seed.py

echo "→ Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
