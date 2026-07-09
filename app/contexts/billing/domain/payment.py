import datetime as dt
from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError
# PaymentStatus é vocabulário compartilhado (str-enum sem comportamento): reusado
# em vez de duplicar, para evitar mapeamento frágil entre dois enums.
from app.models.payment import PaymentStatus

_SCALARS = ("amount", "status", "paid_at", "notes")


@dataclass(eq=False)
class Payment(AggregateRoot):
    student_id: str = ""
    month_key: str = ""
    amount: float = 0.0
    status: PaymentStatus = PaymentStatus.pending
    paid_at: dt.date | None = None
    notes: str | None = None
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None

    @classmethod
    def register(cls, *, id: str, student_id: str, month_key: str, amount: float = 0.0,
                 status: PaymentStatus = PaymentStatus.pending, paid_at: dt.date | None = None,
                 notes: str | None = None) -> "Payment":
        if not student_id:
            raise ValidationError("Aluno é obrigatório")
        if not month_key or not month_key.strip():
            raise ValidationError("Mês de referência é obrigatório")
        return cls(
            id=id, student_id=student_id, month_key=month_key.strip(), amount=amount,
            status=status, paid_at=paid_at, notes=notes,
        )

    def change_fields(self, **fields) -> None:
        for key, value in fields.items():
            if key in _SCALARS:
                setattr(self, key, value)
