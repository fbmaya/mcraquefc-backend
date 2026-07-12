from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ParentStudentLink(Base):
    """Links a parent (User with role=parent) to a student.

    Criado por reconciliação: bate o guardian_email do aluno com o email do
    responsável no login (ver app.contexts.identity — ReconcileParentLinks)."""

    __tablename__ = "parent_student_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parent_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    parent: Mapped["User"] = relationship(back_populates="parent_links")
    student: Mapped["Student"] = relationship(back_populates="parent_links")
