import datetime as dt
import uuid
from app.database import SessionLocal
from app.models.school import School
from app.models.class_ import Class as ClassORM
from app.models.student import Student as StudentORM
from app.models.attendance import AttendanceRecord as RecordORM
from app.contexts.attendance.domain.session import AttendanceSession, AttendanceRecordLine
from app.contexts.attendance.infrastructure.repositories import SqlAlchemyAttendanceRepository


def _seed(db):
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    cls = ClassORM(id=str(uuid.uuid4()), school_id=school.id, name="Sub-9")
    db.add(cls)
    stu = StudentORM(id=str(uuid.uuid4()), school_id=school.id, name="Lucas", guardian_email="p@t.com")
    db.add(stu)
    db.commit()
    return school.id, cls.id, stu.id


def _session(repo, class_id, stu_id, date=dt.date(2026, 6, 1)):
    return AttendanceSession.register(
        id=repo.next_id(), class_id=class_id, date=date, notes="treino",
        records=[AttendanceRecordLine(id=repo.next_record_id(), student_id=stu_id, present=True)],
    )


def test_create_with_records_persists(db_session):
    _, cls_id, stu_id = _seed(db_session)
    repo = SqlAlchemyAttendanceRepository(db_session)
    s = _session(repo, cls_id, stu_id)
    repo.add(s)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = SqlAlchemyAttendanceRepository(fresh).get(s.id)
        assert got is not None and got.class_id == cls_id and got.notes == "treino"
        assert len(got.records) == 1 and got.records[0].present is True
        assert got.records[0].student_id == stu_id
        assert got.created_at is not None
    finally:
        fresh.close()


def test_list_by_school_scoped_and_ordered(db_session):
    school_id, cls_id, stu_id = _seed(db_session)
    repo = SqlAlchemyAttendanceRepository(db_session)
    older = AttendanceSession.register(id=repo.next_id(), class_id=cls_id, date=dt.date(2026, 1, 1), records=[])
    newer = AttendanceSession.register(id=repo.next_id(), class_id=cls_id, date=dt.date(2026, 9, 1), records=[])
    for x in (older, newer):
        repo.add(x)
    db_session.commit()
    got = repo.list_by_school(school_id)
    assert [s.date for s in got] == [dt.date(2026, 9, 1), dt.date(2026, 1, 1)]  # date desc


def test_remove_deletes_session_and_records(db_session):
    _, cls_id, stu_id = _seed(db_session)
    repo = SqlAlchemyAttendanceRepository(db_session)
    s = _session(repo, cls_id, stu_id)
    repo.add(s)
    db_session.commit()
    assert db_session.query(RecordORM).filter(RecordORM.session_id == s.id).count() == 1
    repo.remove(s)
    db_session.commit()
    assert repo.get(s.id) is None
    assert db_session.query(RecordORM).filter(RecordORM.session_id == s.id).count() == 0  # no orphans


def test_school_validation_helpers(db_session):
    school_id, cls_id, stu_id = _seed(db_session)
    repo = SqlAlchemyAttendanceRepository(db_session)
    assert repo.class_belongs_to_school(cls_id, school_id) is True
    assert repo.class_belongs_to_school(cls_id, "OUTRA") is False
    assert repo.students_all_in_school({stu_id}, school_id) is True
    assert repo.students_all_in_school({stu_id, "ghost"}, school_id) is False
    assert repo.students_all_in_school(set(), school_id) is True
