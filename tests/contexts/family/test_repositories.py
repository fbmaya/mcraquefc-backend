import datetime as dt
import uuid
from app.database import SessionLocal
from app.models.school import School
from app.models.license import License, LicenseStatus
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.parent_link import ParentStudentLink
from app.contexts.family.domain.subscription import FamilySubscription
from app.contexts.family.infrastructure.repositories import (
    SqlAlchemyFamilySubscriptionRepository, SqlAlchemyFamilyAccessReader,
)


def _school(db, *, active=True, family_included=False, lic_status=LicenseStatus.active):
    s = School(id=str(uuid.uuid4()), name="E", primary_color="#000", active=active)
    db.add(s)
    db.add(License(id=str(uuid.uuid4()), school_id=s.id, status=lic_status,
                   family_included=family_included))
    db.commit()
    return s.id


def _parent_student(db, school_id, *, active=True):
    p = User(id=str(uuid.uuid4()), school_id=None, name="Mãe", email=f"{uuid.uuid4()}@t.com",
             hashed_password="h", role=UserRole.parent)
    db.add(p)
    stu = Student(id=str(uuid.uuid4()), school_id=school_id, name="Filho",
                  guardian_email="p@t.com", active=active)
    db.add(stu)
    db.add(ParentStudentLink(id=str(uuid.uuid4()), parent_id=p.id, student_id=stu.id))
    db.commit()
    return p.id, stu.id


def test_subscription_roundtrip_and_active_for(db_session):
    school_id = _school(db_session)
    repo = SqlAlchemyFamilySubscriptionRepository(db_session)
    sub = FamilySubscription.open(id=repo.next_id(), parent_id="p1", school_id=school_id,
                                  expires_at=dt.date(2026, 12, 31))
    repo.add(sub)
    db_session.commit()
    fresh = SessionLocal()
    try:
        r = SqlAlchemyFamilySubscriptionRepository(fresh)
        got = r.get(sub.id)
        assert got is not None and got.parent_id == "p1" and got.expires_at == dt.date(2026, 12, 31)
        assert r.active_for("p1", school_id).id == sub.id
    finally:
        fresh.close()


def test_active_for_excludes_cancelled(db_session):
    school_id = _school(db_session)
    repo = SqlAlchemyFamilySubscriptionRepository(db_session)
    sub = FamilySubscription.open(id=repo.next_id(), parent_id="p1", school_id=school_id)
    repo.add(sub)
    db_session.commit()
    sub.cancel()
    repo.save(sub)
    db_session.commit()
    assert repo.active_for("p1", school_id) is None


def test_reader_is_linked_and_student_info(db_session):
    school_id = _school(db_session)
    parent_id, stu_id = _parent_student(db_session, school_id, active=True)
    reader = SqlAlchemyFamilyAccessReader(db_session)
    assert reader.is_linked(parent_id, stu_id) is True
    assert reader.is_linked("ghost", stu_id) is False
    info = reader.student_access_info(stu_id)
    assert info.active is True and info.school_id == school_id
    assert reader.student_access_info("ghost") is None


def test_reader_school_family_included_conditions(db_session):
    reader_of = lambda db: SqlAlchemyFamilyAccessReader(db)
    # incluso + escola ativa + licença ativa → True
    s1 = _school(db_session, family_included=True)
    assert reader_of(db_session).school_family_included(s1) is True
    # incluso mas escola inativa → False
    s2 = _school(db_session, family_included=True, active=False)
    assert reader_of(db_session).school_family_included(s2) is False
    # incluso mas licença suspensa → False
    s3 = _school(db_session, family_included=True, lic_status=LicenseStatus.suspended)
    assert reader_of(db_session).school_family_included(s3) is False
    # não incluso → False
    s4 = _school(db_session, family_included=False)
    assert reader_of(db_session).school_family_included(s4) is False
