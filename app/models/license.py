from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Boolean, Integer, Float, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class PlanType(str, enum.Enum):
    trial   = "trial"
    starter = "starter"
    pro     = "pro"
    elite   = "elite"


class LicenseStatus(str, enum.Enum):
    active    = "active"
    suspended = "suspended"
    cancelled = "cancelled"


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"), unique=True)
    plan: Mapped[PlanType] = mapped_column(Enum(PlanType), default=PlanType.trial)
    status: Mapped[LicenseStatus] = mapped_column(Enum(LicenseStatus), default=LicenseStatus.active)
    max_students: Mapped[int] = mapped_column(Integer, default=30)
    max_coaches: Mapped[int] = mapped_column(Integer, default=2)
    # Family incluso no plano School: responsáveis de alunos ativos têm acesso pago.
    family_included: Mapped[bool] = mapped_column(Boolean, default=False)
    family_price_per_student: Mapped[float | None] = mapped_column(Float)
    expires_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    school: Mapped["School"] = relationship(back_populates="license")
