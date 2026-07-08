import uuid
from app.database import SessionLocal
from app.models.school import School
from app.models.student import Student as StudentORM
from app.contexts.school.domain.school_class import SchoolClass
from app.contexts.school.infrastructure.repositories import (
    SqlAlchemyClassRepository, SqlAlchemyEnrollmentRepository, SqlAlchemyStudentLookup,
)


def _seed_school_and_student(db):
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    stu = StudentORM(id=str(uuid.uuid4()), school_id=school.id, name="Lucas", guardian_email="p@t.com")
    db.add(stu)
    db.commit()
    return school.id, stu.id


def test_class_roundtrip_and_update_persists(db_session):
    school_id, _ = _seed_school_and_student(db_session)
    repo = SqlAlchemyClassRepository(db_session)
    c = SchoolClass.register(id=repo.next_id(), school_id=school_id, name="Sub-9 A", period="Manhã")
    repo.add(c)
    db_session.commit()

    # update via domain + add, then re-read from a FRESH session
    c.change(period="Noite")
    repo.add(c)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = SqlAlchemyClassRepository(fresh).get(c.id)
        assert got is not None and got.period == "Noite" and got.name == "Sub-9 A"
    finally:
        fresh.close()


def test_list_by_school_scoped(db_session):
    school_id, _ = _seed_school_and_student(db_session)
    repo = SqlAlchemyClassRepository(db_session)
    repo.add(SchoolClass.register(id=repo.next_id(), school_id=school_id, name="A"))
    repo.add(SchoolClass.register(id=repo.next_id(), school_id="OTHER", name="B"))
    db_session.commit()
    assert {c.name for c in repo.list_by_school(school_id)} == {"A"}


def test_enrollment_create_find_deactivate_and_active_ids(db_session):
    school_id, stu_id = _seed_school_and_student(db_session)
    classes = SqlAlchemyClassRepository(db_session)
    c = SchoolClass.register(id=classes.next_id(), school_id=school_id, name="A")
    classes.add(c)
    db_session.commit()
    enr = SqlAlchemyEnrollmentRepository(db_session)
    assert enr.find(c.id, stu_id) is None
    enr.create(enr.next_id(), c.id, stu_id)
    db_session.commit()
    found = enr.find(c.id, stu_id)
    assert found is not None and found.active is True
    assert classes.active_student_ids(c.id) == [stu_id]
    enr.set_active(c.id, stu_id, False)
    db_session.commit()
    assert enr.find(c.id, stu_id).active is False
    assert classes.active_student_ids(c.id) == []


def test_student_lookup_belongs_to_school(db_session):
    school_id, stu_id = _seed_school_and_student(db_session)
    lookup = SqlAlchemyStudentLookup(db_session)
    assert lookup.belongs_to_school(stu_id, school_id) is True
    assert lookup.belongs_to_school(stu_id, "OTHER") is False
    assert lookup.belongs_to_school("nope", school_id) is False
