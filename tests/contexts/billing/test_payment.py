import datetime as dt
import pytest
from app.shared.domain.errors import ValidationError
from app.models.payment import PaymentStatus
from app.contexts.billing.domain.payment import Payment


def make(**kw):
    base = dict(id="p1", student_id="stu1", month_key="2026-06")
    base.update(kw)
    return Payment.register(**base)


def test_register_requires_student():
    with pytest.raises(ValidationError):
        make(student_id="")


def test_register_requires_month_key():
    with pytest.raises(ValidationError):
        make(month_key="  ")


def test_register_sets_fields_and_defaults():
    p = make(amount=150.0, status=PaymentStatus.paid)
    assert p.student_id == "stu1"
    assert p.month_key == "2026-06"
    assert p.amount == 150.0
    assert p.status == PaymentStatus.paid


def test_register_default_status_pending():
    assert make().status == PaymentStatus.pending


def test_change_fields_updates_only_scalars():
    p = make()
    p.change_fields(amount=200.0, status=PaymentStatus.paid, student_id="HACK", month_key="HACK")
    assert p.amount == 200.0
    assert p.status == PaymentStatus.paid
    assert p.student_id == "stu1"   # identity untouched
    assert p.month_key == "2026-06"
