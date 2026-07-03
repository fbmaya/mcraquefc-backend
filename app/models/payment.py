from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Float, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    exempt = "exempt"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    month_key: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    paid_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    student: Mapped["Student"] = relationship(back_populates="payments")
