from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Integer, Boolean, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"))
    date: Mapped[date] = mapped_column(Date, index=True)
    opponent: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(300))
    home: Mapped[bool] = mapped_column(Boolean, default=True)
    score_us: Mapped[int | None] = mapped_column(Integer)
    score_them: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    school: Mapped["School"] = relationship(back_populates="matches")
    stats: Mapped[list["MatchStat"]] = relationship(back_populates="match")


class MatchStat(Base):
    __tablename__ = "match_stats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float | None] = mapped_column(Float)
    played: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500))

    match: Mapped["Match"] = relationship(back_populates="stats")
    student: Mapped["Student"] = relationship(back_populates="match_stats")
