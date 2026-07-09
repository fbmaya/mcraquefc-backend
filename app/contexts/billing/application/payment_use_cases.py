from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.contexts.billing.domain.payment import Payment
from app.contexts.billing.domain.repositories import PaymentRepository
from app.contexts.billing.application.payment_dtos import NewPayment, PaymentView

_SCALARS = ("amount", "status", "paid_at", "notes")


class StudentNotFound(DomainError):
    pass


class DuplicatePayment(DomainError):
    pass


class PaymentNotFound(DomainError):
    pass


def _require(payments: PaymentRepository, school_id: str, payment_id: str) -> Payment:
    p = payments.get(payment_id)
    if p is None or not payments.student_belongs_to_school(p.student_id, school_id):
        raise PaymentNotFound("Pagamento não encontrado")
    return p


class CreatePayment:
    def __init__(self, payments: PaymentRepository, uow: UnitOfWork):
        self.payments, self.uow = payments, uow

    def execute(self, *, school_id: str, data: NewPayment) -> PaymentView:
        if not self.payments.student_belongs_to_school(data.student_id, school_id):
            raise StudentNotFound("Aluno não encontrado")
        if self.payments.exists_for_student_month(data.student_id, data.month_key):
            raise DuplicatePayment("Pagamento já existe para esse mês")
        payment = Payment.register(
            id=self.payments.next_id(), student_id=data.student_id, month_key=data.month_key,
            amount=data.amount, status=data.status, paid_at=data.paid_at, notes=data.notes,
        )
        self.payments.add(payment)
        self.uow.commit()
        saved = self.payments.get(payment.id)  # relê p/ updated_at
        return PaymentView.of(saved)


class ListPayments:
    def __init__(self, payments: PaymentRepository):
        self.payments = payments

    def execute(self, *, school_id: str, month_key: str | None = None,
                student_id: str | None = None) -> list[PaymentView]:
        return [PaymentView.of(p) for p in self.payments.list_by_school(school_id, month_key, student_id)]


class ListPaymentsForStudent:
    """Portal do responsável: pagamentos de um aluno (sem escopo de escola)."""

    def __init__(self, payments: PaymentRepository):
        self.payments = payments

    def execute(self, *, student_id: str) -> list[PaymentView]:
        return [PaymentView.of(p) for p in self.payments.list_by_student(student_id)]


class UpdatePayment:
    def __init__(self, payments: PaymentRepository, uow: UnitOfWork):
        self.payments, self.uow = payments, uow

    def execute(self, *, school_id: str, payment_id: str, changes: dict) -> PaymentView:
        payment = _require(self.payments, school_id, payment_id)
        fields = {k: v for k, v in changes.items() if k in _SCALARS and v is not None}
        payment.change_fields(**fields)
        self.payments.save(payment)
        self.uow.commit()
        return PaymentView.of(payment)


class DeletePayment:
    def __init__(self, payments: PaymentRepository, uow: UnitOfWork):
        self.payments, self.uow = payments, uow

    def execute(self, *, school_id: str, payment_id: str) -> None:
        self.payments.remove(_require(self.payments, school_id, payment_id))
        self.uow.commit()
