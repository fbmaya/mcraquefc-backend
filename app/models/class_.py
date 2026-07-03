from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"))
    name: Mapped[str] = mapped_column(String(200))
    age_group: Mapped[str | None] = mapped_column(String(50))
    schedule: Mapped[str | None] = mapped_column(String(200))
    coach_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    school: Mapped["School"] = relationship(back_populates="classes")
    coach: Mapped["User | None"] = relationship()
    enrollments: Mapped[list["ClassEnrollment"]] = relationship(back_populates="class_")
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(back_populates="class_")

    @property
    def student_ids(self) -> list[str]:
        """IDs of currently enrolled (active) students."""
        return [e.student_id for e in self.enrollments if e.active]


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    active: Mapped[bool] = mapped_column(default=True)

    class_: Mapped["Class"] = relationship(back_populates="enrollments")
    student: Mapped["Student"] = relationship(back_populates="class_enrollments")
