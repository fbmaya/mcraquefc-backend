from datetime import date, datetime
from pydantic import BaseModel
from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    student_id: str
    month_key: str  # YYYY-MM
    amount: float = 0.0
    status: PaymentStatus = PaymentStatus.pending
    paid_at: date | None = None
    notes: str | None = None


class PaymentUpdate(BaseModel):
    amount: float | None = None
    status: PaymentStatus | None = None
    paid_at: date | None = None
    notes: str | None = None


class PaymentOut(BaseModel):
    id: str
    student_id: str
    month_key: str
    amount: float
    status: PaymentStatus
    paid_at: date | None
    notes: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}
