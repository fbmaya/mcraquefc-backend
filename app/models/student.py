from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Integer, Float, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"))
    name: Mapped[str] = mapped_column(String(200), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[str | None] = mapped_column(String(100))
    foot: Mapped[str | None] = mapped_column(String(20))
    guardian_name: Mapped[str | None] = mapped_column(String(200))
    guardian_phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(String(1000))
    access_code: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    school: Mapped["School"] = relationship(back_populates="students")
    class_enrollments: Mapped[list["ClassEnrollment"]] = relationship(back_populates="student")
    payments: Mapped[list["Payment"]] = relationship(back_populates="student")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="student")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="student")
    match_stats: Mapped[list["MatchStat"]] = relationship(back_populates="student")
    parent_links: Mapped[list["ParentStudentLink"]] = relationship(back_populates="student")
