"""Política de licença (tenancy) usada como guarda na camada de interface.

Consumida por vários contextos (Athletes ao criar aluno; Identity/auth e o
dependency `get_current_user` ao validar o tenant). Opera direto sobre a Session
e levanta HTTPException por ser um guard de borda — os limites por plano são o
idioma publicado do contexto Platform/Tenancy.

Todos os helpers são no-op quando a escola não tem licença (grandfathered).
O limite de professores na criação de staff vive no caso de uso CreateStaff.
"""
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.license import License, LicenseStatus
from app.models.school import School
from app.models.student import Student
from app.models.user import User


def get_license(db: Session, school_id: str) -> License | None:
    return db.query(License).filter(License.school_id == school_id).first()


def assert_can_add_student(db: Session, school_id: str) -> None:
    lic = get_license(db, school_id)
    if lic is None:
        return
    count = db.query(func.count(Student.id)).filter(Student.school_id == school_id).scalar() or 0
    if count >= lic.max_students:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite de alunos do plano atingido ({lic.max_students}). Faça upgrade para adicionar mais.",
        )


def assert_tenant_active(db: Session, user: User) -> None:
    """Bloqueia staff de escola inativa ou licença suspensa/cancelada.

    platform_admin e responsáveis (school_id None) nunca são bloqueados aqui.
    """
    if not user.school_id:
        return
    school = db.get(School, user.school_id)
    if school is None or not school.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Escolinha inativa. Entre em contato com a plataforma.",
        )
    lic = get_license(db, user.school_id)
    if lic is not None and lic.status != LicenseStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Licença suspensa ou cancelada. Entre em contato com a plataforma.",
        )
