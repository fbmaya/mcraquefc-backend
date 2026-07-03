"""Bring the database schema up to date via Alembic.

Handles three cases automatically:
  - empty DB               → upgrade head cria todo o schema
  - existing DB, no alembic → stamp head (adota o schema atual) + upgrade
  - DB já versionado        → upgrade head aplica migrations pendentes
"""
import os
import sys

# garante que a raiz do projeto (onde fica o pacote `app` e o alembic.ini)
# esteja no sys.path, independente de como o script é invocado
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect
from alembic.config import Config
from alembic import command

from app.database import engine

inspector = inspect(engine)
tables = set(inspector.get_table_names())

cfg = Config("alembic.ini")

if "schools" in tables and "alembic_version" not in tables:
    # Banco criado antes do Alembic (via create_all). Marca como 'head'
    # para o upgrade seguinte só aplicar migrations novas, sem recriar tabelas.
    print("  → banco pré-existente sem Alembic: aplicando 'stamp head'")
    command.stamp(cfg, "head")

command.upgrade(cfg, "head")
print("  → schema atualizado (alembic upgrade head)")
