import uuid

from sqlalchemy.orm import Session

from app.contexts.billing.domain.payment import Payment
from app.contexts.billing.domain.repositories import PaymentRepository
from app.models.payment import Payment as PaymentORM
from app.models.student import Student as StudentORM

_SCALARS = ("amount", "status", "paid_at", "notes")


def _to_domain(row: PaymentORM) -> Payment:
    return Payment(
        id=row.id, student_id=row.student_id, month_key=row.month_key, amount=row.amount,
        status=row.status, paid_at=row.paid_at, notes=row.notes,
        created_at=row.created_at, updated_at=row.updated_at,
    )


class SqlAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def add(self, payment: Payment) -> None:
        self.session.add(PaymentORM(
            id=payment.id, student_id=payment.student_id, month_key=payment.month_key,
            amount=payment.amount, status=payment.status, paid_at=payment.paid_at, notes=payment.notes,
        ))

    def save(self, payment: Payment) -> None:
        row = self.session.get(PaymentORM, payment.id)
        if row is None:
            return
        for field_name in _SCALARS:
            setattr(row, field_name, getattr(payment, field_name))

    def get(self, payment_id: str) -> Payment | None:
        row = self.session.get(PaymentORM, payment_id)
        return _to_domain(row) if row else None

    def list_by_school(self, school_id: str, month_key: str | None = None,
                       student_id: str | None = None) -> list[Payment]:
        q = (
            self.session.query(PaymentORM)
            .join(StudentORM, PaymentORM.student_id == StudentORM.id)
            .filter(StudentORM.school_id == school_id)
        )
        if month_key:
            q = q.filter(PaymentORM.month_key == month_key)
        if student_id:
            q = q.filter(PaymentORM.student_id == student_id)
        return [_to_domain(r) for r in q.order_by(PaymentORM.month_key.desc()).all()]

    def remove(self, payment: Payment) -> None:
        row = self.session.get(PaymentORM, payment.id)
        if row:
            self.session.delete(row)

    def student_belongs_to_school(self, student_id: str, school_id: str) -> bool:
        row = self.session.get(StudentORM, student_id)
        return row is not None and row.school_id == school_id

    def exists_for_student_month(self, student_id: str, month_key: str) -> bool:
        return (
            self.session.query(PaymentORM.id)
            .filter(PaymentORM.student_id == student_id, PaymentORM.month_key == month_key)
            .first()
            is not None
        )
