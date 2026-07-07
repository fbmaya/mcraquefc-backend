"""
Cria (ou atualiza a senha de) um usuário platform_admin.

Idempotente: se o email já existe, atualiza a senha e garante role=platform_admin;
senão, cria. Uso pensado para bootstrap do 1º admin em produção, rodado via
Cloud Run Job dentro da VPC (mesma imagem do backend, com DATABASE_URL injetado).

Env:
  ADMIN_EMAIL     (obrigatório)
  ADMIN_PASSWORD  (obrigatório)
  ADMIN_NAME      (opcional, default "Admin Plataforma")

Uso: python scripts/create_admin.py
"""
import os
import sys
import uuid

# Permite rodar de qualquer working dir (insere a raiz do projeto no sys.path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.auth.jwt import hash_password

email = os.environ.get("ADMIN_EMAIL")
password = os.environ.get("ADMIN_PASSWORD")
name = os.environ.get("ADMIN_NAME", "Admin Plataforma")

if not email or not password:
    sys.exit("ADMIN_EMAIL e ADMIN_PASSWORD são obrigatórios.")

db = SessionLocal()
user = db.query(User).filter(User.email == email).first()

if user:
    user.hashed_password = hash_password(password)
    user.role = UserRole.platform_admin
    action = "atualizado"
else:
    user = User(
        id=str(uuid.uuid4()),
        school_id=None,
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role=UserRole.platform_admin,
    )
    db.add(user)
    action = "criado"

db.commit()
print(f"platform_admin {action}: {email}")
