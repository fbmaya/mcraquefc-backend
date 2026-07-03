from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ParentStudentLink(Base):
    """Links a parent (User with role=parent) to a student via access_code."""

    __tablename__ = "parent_student_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parent_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    parent: Mapped["User"] = relationship(back_populates="parent_links")
    student: Mapped["Student"] = relationship(back_populates="parent_links")
