"""Vínculo pai↔aluno por email do responsável (substitui o access_code).

O staff cadastra o aluno com `guardian_email`. Quando o responsável entra
(senha ou Google), reconciliamos: para todo Student cujo `guardian_email` bate
com o email do usuário (case-insensitive), garantimos um ParentStudentLink.
Sem código de vínculo, sem tela de vincular.
"""
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.parent_link import ParentStudentLink


def reconcile_parent_links(db: Session, user: User) -> int:
    """Cria os vínculos que faltam para este responsável. Retorna quantos criou."""
    if user.role != UserRole.parent or not user.email:
        return 0

    email = user.email.strip().lower()
    students = db.query(Student).filter(func.lower(Student.guardian_email) == email).all()
    if not students:
        return 0

    already = {
        link.student_id
        for link in db.query(ParentStudentLink).filter(ParentStudentLink.parent_id == user.id).all()
    }

    created = 0
    for student in students:
        if student.id not in already:
            db.add(ParentStudentLink(id=str(uuid.uuid4()), parent_id=user.id, student_id=student.id))
            created += 1

    if created:
        db.commit()
    return created
