import datetime as dt
import pytest
from app.contexts.attendance.domain.session import AttendanceSession
from app.contexts.attendance.domain.repositories import AttendanceRepository
from app.contexts.attendance.application.attendance_dtos import NewSession, NewRecord
from app.contexts.attendance.application import attendance_use_cases as uc


class FakeSessions(AttendanceRepository):
    def __init__(self, classes: dict[str, str] | None = None, students: dict[str, str] | None = None):
        self.items: dict[str, AttendanceSession] = {}
        self.classes = classes or {}    # class_id -> school_id
        self.students = students or {}   # student_id -> school_id
        self._a = 0
        self._r = 0

    def add(self, s): self.items[s.id] = s
    def get(self, sid): return self.items.get(sid)

    def list_by_school(self, school_id, class_id=None):
        out = [s for s in self.items.values() if self.classes.get(s.class_id) == school_id]
        if class_id:
            out = [s for s in out if s.class_id == class_id]
        return out

    def list_by_student(self, student_id):
        return [s for s in self.items.values()
                if any(r.student_id == student_id for r in s.records)]

    def remove(self, s): self.items.pop(s.id, None)
    def class_belongs_to_school(self, class_id, school_id): return self.classes.get(class_id) == school_id
    def students_all_in_school(self, student_ids, school_id):
        return all(self.students.get(sid) == school_id for sid in student_ids)

    def next_id(self):
        self._a += 1
        return f"a{self._a}"

    def next_record_id(self):
        self._r += 1
        return f"r{self._r}"


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def _new(**kw):
    base = dict(class_id="cls1", date=dt.date(2026, 6, 1))
    base.update(kw)
    return NewSession(**base)


def test_create_session_with_records_returns_view():
    repo = FakeSessions(classes={"cls1": "sch1"}, students={"stu1": "sch1", "stu2": "sch1"})
    uow = FakeUoW()
    view = uc.CreateSession(repo, uow).execute(school_id="sch1", data=_new(
        notes="treino", records=[NewRecord(student_id="stu1", present=True), NewRecord(student_id="stu2")]))
    assert view.class_id == "cls1"
    assert view.notes == "treino"
    assert len(view.records) == 2
    assert {r.student_id for r in view.records} == {"stu1", "stu2"}
    assert all(r.id for r in view.records)  # record ids assigned
    assert uow.commits == 1


def test_create_rejects_class_of_other_school():
    repo = FakeSessions(classes={"cls1": "OUTRA"})
    with pytest.raises(uc.ClassNotFound):
        uc.CreateSession(repo, FakeUoW()).execute(school_id="sch1", data=_new())


def test_create_rejects_foreign_student():
    repo = FakeSessions(classes={"cls1": "sch1"}, students={"stu1": "OUTRA"})
    with pytest.raises(uc.InvalidRecords):
        uc.CreateSession(repo, FakeUoW()).execute(
            school_id="sch1", data=_new(records=[NewRecord(student_id="stu1", present=True)]))


def test_list_sessions_scoped_by_school_and_class():
    repo = FakeSessions(classes={"cls1": "sch1", "cls2": "sch1", "cls3": "sch2"})
    c, uow = uc.CreateSession(repo, FakeUoW()), FakeUoW()
    uc.CreateSession(repo, uow).execute(school_id="sch1", data=_new(class_id="cls1"))
    uc.CreateSession(repo, uow).execute(school_id="sch1", data=_new(class_id="cls2"))
    uc.CreateSession(repo, uow).execute(school_id="sch2", data=_new(class_id="cls3"))
    assert len(uc.ListSessions(repo).execute(school_id="sch1")) == 2
    scoped = uc.ListSessions(repo).execute(school_id="sch1", class_id="cls1")
    assert [s.class_id for s in scoped] == ["cls1"]


def test_delete_session():
    repo = FakeSessions(classes={"cls1": "sch1"})
    v = uc.CreateSession(repo, FakeUoW()).execute(school_id="sch1", data=_new())
    uc.DeleteSession(repo, FakeUoW()).execute(school_id="sch1", session_id=v.id)
    assert repo.get(v.id) is None


def test_delete_session_wrong_school_raises():
    repo = FakeSessions(classes={"cls1": "sch1"})
    v = uc.CreateSession(repo, FakeUoW()).execute(school_id="sch1", data=_new())
    with pytest.raises(uc.SessionNotFound):
        uc.DeleteSession(repo, FakeUoW()).execute(school_id="OUTRA", session_id=v.id)
