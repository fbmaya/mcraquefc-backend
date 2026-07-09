import datetime as dt
import uuid
from app.database import SessionLocal
from app.models.school import School
from app.models.student import Student as StudentORM
from app.models.payment import PaymentStatus
from app.contexts.billing.domain.payment import Payment
from app.contexts.billing.infrastructure.repositories import SqlAlchemyPaymentRepository


def _seed(db):
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    stu = StudentORM(id=str(uuid.uuid4()), school_id=school.id, name="Lucas", guardian_email="p@t.com")
    db.add(stu)
    db.commit()
    return school.id, stu.id


def _payment(repo, stu_id, month_key="2026-06", amount=150.0):
    return Payment.register(id=repo.next_id(), student_id=stu_id, month_key=month_key,
                            amount=amount, status=PaymentStatus.paid)


def test_create_persists(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyPaymentRepository(db_session)
    p = _payment(repo, stu_id)
    repo.add(p)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = SqlAlchemyPaymentRepository(fresh).get(p.id)
        assert got is not None and got.amount == 150.0 and got.status == PaymentStatus.paid
        assert got.month_key == "2026-06" and got.updated_at is not None
    finally:
        fresh.close()


def test_update_scalar_persists_from_fresh_session(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyPaymentRepository(db_session)
    p = _payment(repo, stu_id, amount=100.0)
    repo.add(p)
    db_session.commit()
    p.change_fields(amount=250.0, status=PaymentStatus.overdue)
    repo.save(p)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = SqlAlchemyPaymentRepository(fresh).get(p.id)
        assert got.amount == 250.0 and got.status == PaymentStatus.overdue
    finally:
        fresh.close()


def test_list_by_school_scoped_and_filtered(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyPaymentRepository(db_session)
    for x in (_payment(repo, stu_id, "2026-05"), _payment(repo, stu_id, "2026-07")):
        repo.add(x)
    # other school payment must not leak
    other = StudentORM(id=str(uuid.uuid4()), school_id=str(uuid.uuid4()), name="X", guardian_email="x@t.com")
    db_session.add(other)
    db_session.commit()
    repo.add(_payment(repo, other.id, "2026-06"))
    db_session.commit()
    got = repo.list_by_school(school_id)
    assert [p.month_key for p in got] == ["2026-07", "2026-05"]  # month desc
    assert [p.month_key for p in repo.list_by_school(school_id, month_key="2026-05")] == ["2026-05"]


def test_exists_for_student_month(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyPaymentRepository(db_session)
    repo.add(_payment(repo, stu_id, "2026-06"))
    db_session.commit()
    assert repo.exists_for_student_month(stu_id, "2026-06") is True
    assert repo.exists_for_student_month(stu_id, "2026-09") is False


def test_remove(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyPaymentRepository(db_session)
    p = _payment(repo, stu_id)
    repo.add(p)
    db_session.commit()
    repo.remove(p)
    db_session.commit()
    assert repo.get(p.id) is None


def test_student_belongs_to_school(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyPaymentRepository(db_session)
    assert repo.student_belongs_to_school(stu_id, school_id) is True
    assert repo.student_belongs_to_school(stu_id, "OUTRA") is False
    assert repo.student_belongs_to_school("ghost", school_id) is False
