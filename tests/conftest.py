import os
import tempfile
import pytest

# Env obrigatório do app.config ANTES de qualquer import de app.*
os.environ.setdefault("SECRET_KEY", "test-secret")
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")


@pytest.fixture()
def db_session():
    """Sessão SQLAlchemy limpa sobre um schema criado do zero (create_all)."""
    from app.database import Base, engine, SessionLocal
    import app.models  # noqa: F401 — registra as tabelas
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
