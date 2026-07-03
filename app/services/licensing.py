"""Business rules tied to a school's license: plan limits + tenant status.

All helpers are no-ops when the school has no license (grandfathered), so
existing setups keep working; enforcement only kicks in where a license exists.
"""
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.license import License, LicenseStatus
from app.models.school import School
from app.models.student import Student
from app.models.user import User, UserRole


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


def assert_can_add_coach(db: Session, school_id: str) -> None:
    lic = get_license(db, school_id)
    if lic is None:
        return
    count = (
        db.query(func.count(User.id))
        .filter(User.school_id == school_id, User.role == UserRole.coach)
        .scalar()
    ) or 0
    if count >= lic.max_coaches:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limite de professores do plano atingido ({lic.max_coaches}). Faça upgrade para adicionar mais.",
        )


def assert_tenant_active(db: Session, user: User) -> None:
    """Block staff of an inactive school or a suspended/cancelled license.

    platform_admin and parents (school_id is None) are never blocked here.
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
