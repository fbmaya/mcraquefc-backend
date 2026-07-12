from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    class_: Mapped["Class"] = relationship(back_populates="attendance_sessions")
    records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="session")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("attendance_sessions.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    present: Mapped[bool] = mapped_column(Boolean, default=False)
    justified: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(String(300))

    session: Mapped["AttendanceSession"] = relationship(back_populates="records")
    student: Mapped["Student"] = relationship(back_populates="attendance_records")
