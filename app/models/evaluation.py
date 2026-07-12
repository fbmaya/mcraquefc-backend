from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _avg(*values: "float | None") -> "float | None":
    """Average of the provided scores, ignoring None. Returns None if all None."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 1)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    evaluated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)

    # ── Granular skills (0-10) ──────────────────────────────────
    # Technical
    passing: Mapped[float | None] = mapped_column(Float)
    finishing: Mapped[float | None] = mapped_column(Float)
    dribbling: Mapped[float | None] = mapped_column(Float)
    # Physical
    speed: Mapped[float | None] = mapped_column(Float)
    stamina: Mapped[float | None] = mapped_column(Float)
    agility: Mapped[float | None] = mapped_column(Float)
    # Tactical
    positioning: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[float | None] = mapped_column(Float)
    # Behavioral / mental
    discipline: Mapped[float | None] = mapped_column(Float)
    teamwork: Mapped[float | None] = mapped_column(Float)
    attitude: Mapped[float | None] = mapped_column(Float)
    commitment: Mapped[float | None] = mapped_column(Float)
    leadership: Mapped[float | None] = mapped_column(Float)

    notes: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    student: Mapped["Student"] = relationship(back_populates="evaluations")
    evaluator: Mapped["User | None"] = relationship()

    # ── Summary axes (computed, surfaced in the radar) ──────────
    @property
    def technique(self) -> "float | None":
        return _avg(self.passing, self.finishing, self.dribbling)

    @property
    def physical(self) -> "float | None":
        return _avg(self.speed, self.stamina, self.agility)

    @property
    def tactical(self) -> "float | None":
        return _avg(self.positioning, self.decision)

    @property
    def mindset(self) -> "float | None":
        return _avg(self.attitude, self.commitment)

    @property
    def overall(self) -> "float | None":
        """Single 0-10 score across every recorded skill."""
        return _avg(
            self.passing, self.finishing, self.dribbling,
            self.speed, self.stamina, self.agility,
            self.positioning, self.decision,
            self.discipline, self.teamwork, self.attitude,
            self.commitment, self.leadership,
        )
