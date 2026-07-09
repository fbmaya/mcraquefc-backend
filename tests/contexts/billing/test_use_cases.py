import pytest
from app.models.payment import PaymentStatus
from app.contexts.billing.domain.payment import Payment
from app.contexts.billing.domain.repositories import PaymentRepository
from app.contexts.billing.application.payment_dtos import NewPayment
from app.contexts.billing.application import payment_use_cases as uc


class FakePayments(PaymentRepository):
    def __init__(self, students: dict[str, str] | None = None):
        self.items: dict[str, Payment] = {}
        self.students = students or {}   # student_id -> school_id
        self._n = 0

    def add(self, p): self.items[p.id] = p
    def save(self, p): self.items[p.id] = p
    def get(self, pid): return self.items.get(pid)

    def list_by_school(self, school_id, month_key=None, student_id=None):
        out = [p for p in self.items.values() if self.students.get(p.student_id) == school_id]
        if month_key:
            out = [p for p in out if p.month_key == month_key]
        if student_id:
            out = [p for p in out if p.student_id == student_id]
        return out

    def list_by_student(self, student_id):
        return [p for p in self.items.values() if p.student_id == student_id]

    def remove(self, p): self.items.pop(p.id, None)
    def student_belongs_to_school(self, student_id, school_id): return self.students.get(student_id) == school_id
    def exists_for_student_month(self, student_id, month_key):
        return any(p.student_id == student_id and p.month_key == month_key for p in self.items.values())

    def next_id(self):
        self._n += 1
        return f"p{self._n}"


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def _new(**kw):
    base = dict(student_id="stu1", month_key="2026-06")
    base.update(kw)
    return NewPayment(**base)


def test_create_payment_returns_view():
    repo = FakePayments(students={"stu1": "sch1"})
    uow = FakeUoW()
    view = uc.CreatePayment(repo, uow).execute(school_id="sch1", data=_new(amount=150.0, status=PaymentStatus.paid))
    assert view.student_id == "stu1" and view.amount == 150.0 and view.status == PaymentStatus.paid
    assert uow.commits == 1


def test_create_rejects_foreign_student():
    repo = FakePayments(students={"stu1": "OUTRA"})
    with pytest.raises(uc.StudentNotFound):
        uc.CreatePayment(repo, FakeUoW()).execute(school_id="sch1", data=_new())


def test_create_rejects_duplicate_month():
    repo = FakePayments(students={"stu1": "sch1"})
    uc.CreatePayment(repo, FakeUoW()).execute(school_id="sch1", data=_new())
    with pytest.raises(uc.DuplicatePayment):
        uc.CreatePayment(repo, FakeUoW()).execute(school_id="sch1", data=_new())


def test_list_scoped_by_school_and_filters():
    repo = FakePayments(students={"stu1": "sch1", "stu2": "sch1", "stu3": "sch2"})
    c = lambda **kw: uc.CreatePayment(repo, FakeUoW()).execute(school_id=kw.pop("school"), data=_new(**kw))
    c(school="sch1", student_id="stu1", month_key="2026-06")
    c(school="sch1", student_id="stu2", month_key="2026-07")
    c(school="sch2", student_id="stu3", month_key="2026-06")
    assert len(uc.ListPayments(repo).execute(school_id="sch1")) == 2
    only_june = uc.ListPayments(repo).execute(school_id="sch1", month_key="2026-06")
    assert [p.student_id for p in only_june] == ["stu1"]
    only_stu2 = uc.ListPayments(repo).execute(school_id="sch1", student_id="stu2")
    assert [p.student_id for p in only_stu2] == ["stu2"]


def test_update_changes_scalars_only():
    repo = FakePayments(students={"stu1": "sch1"})
    v = uc.CreatePayment(repo, FakeUoW()).execute(school_id="sch1", data=_new())
    out = uc.UpdatePayment(repo, FakeUoW()).execute(
        school_id="sch1", payment_id=v.id, changes={"amount": 99.0, "status": PaymentStatus.paid})
    assert out.amount == 99.0 and out.status == PaymentStatus.paid
    assert out.month_key == "2026-06"  # untouched


def test_update_wrong_school_raises():
    repo = FakePayments(students={"stu1": "sch1"})
    v = uc.CreatePayment(repo, FakeUoW()).execute(school_id="sch1", data=_new())
    with pytest.raises(uc.PaymentNotFound):
        uc.UpdatePayment(repo, FakeUoW()).execute(school_id="OUTRA", payment_id=v.id, changes={"amount": 1.0})


def test_delete_payment():
    repo = FakePayments(students={"stu1": "sch1"})
    v = uc.CreatePayment(repo, FakeUoW()).execute(school_id="sch1", data=_new())
    uc.DeletePayment(repo, FakeUoW()).execute(school_id="sch1", payment_id=v.id)
    assert repo.get(v.id) is None
