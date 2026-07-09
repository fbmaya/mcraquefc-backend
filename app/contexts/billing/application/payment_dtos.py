import datetime as dt
from dataclasses import dataclass

from app.models.payment import PaymentStatus
from app.contexts.billing.domain.payment import Payment


@dataclass
class NewPayment:
    student_id: str
    month_key: str
    amount: float = 0.0
    status: PaymentStatus = PaymentStatus.pending
    paid_at: dt.date | None = None
    notes: str | None = None


@dataclass
class PaymentView:
    id: str
    student_id: str
    month_key: str
    amount: float
    status: PaymentStatus
    paid_at: dt.date | None
    notes: str | None
    updated_at: dt.datetime | None

    @classmethod
    def of(cls, p: Payment) -> "PaymentView":
        return cls(
            id=p.id, student_id=p.student_id, month_key=p.month_key, amount=p.amount,
            status=p.status, paid_at=p.paid_at, notes=p.notes, updated_at=p.updated_at,
        )
