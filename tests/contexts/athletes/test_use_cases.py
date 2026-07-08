import pytest
from app.shared.domain.errors import ValidationError
from app.shared.domain.value_objects import Email
from app.contexts.athletes.domain.student import Student, matches_guardian
from app.contexts.athletes.domain.repositories import StudentRepository, ParentLinkRepository
from app.contexts.athletes.application.dtos import NewStudent
from app.contexts.athletes.application import use_cases as uc


class FakeStudents(StudentRepository):
    def __init__(self):
        self.items: dict[str, Student] = {}
        self._seq = 0

    def add(self, s): self.items[s.id] = s
    def get(self, sid): return self.items.get(sid)
    def list_by_school(self, school_id): return [s for s in self.items.values() if s.school_id == school_id]
    def list_by_guardian_email(self, email): return [s for s in self.items.values() if matches_guardian(s, email)]
    def remove(self, s): self.items.pop(s.id, None)
    def next_id(self):
        self._seq += 1
        return f"s{self._seq}"


class FakeLinks(ParentLinkRepository):
    def __init__(self):
        self.links: set[tuple[str, str]] = set()
        self._seq = 0

    def student_ids_for_parent(self, pid): return {sid for (p, sid) in self.links if p == pid}
    def link(self, parent_id, student_id): self.links.add((parent_id, student_id))
    def next_id(self):
        self._seq += 1
        return f"l{self._seq}"


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def test_register_student_creates_and_commits():
    students, uow = FakeStudents(), FakeUoW()
    view = uc.RegisterStudent(students, uow).execute(
        school_id="sch1", data=NewStudent(name="Lucas", guardian_email="PAI@t.com", position="Ponta"))
    assert view.name == "Lucas"
    assert view.guardian_email == "pai@t.com"
    assert uow.commits == 1
    assert students.get(view.id) is not None


def test_register_rejects_invalid_email():
    students, uow = FakeStudents(), FakeUoW()
    with pytest.raises(ValidationError):
        uc.RegisterStudent(students, uow).execute(
            school_id="sch1", data=NewStudent(name="X", guardian_email="naoehemail"))


def test_list_students_scoped_by_school():
    students, uow = FakeStudents(), FakeUoW()
    reg = uc.RegisterStudent(students, uow)
    reg.execute(school_id="sch1", data=NewStudent(name="A", guardian_email="a@t.com"))
    reg.execute(school_id="sch2", data=NewStudent(name="B", guardian_email="b@t.com"))
    views = uc.ListStudents(students).execute(school_id="sch1")
    assert [v.name for v in views] == ["A"]


def test_get_student_wrong_school_raises_not_found():
    students, uow = FakeStudents(), FakeUoW()
    v = uc.RegisterStudent(students, uow).execute(school_id="sch1", data=NewStudent(name="A", guardian_email="a@t.com"))
    with pytest.raises(uc.StudentNotFound):
        uc.GetStudent(students).execute(school_id="OUTRA", student_id=v.id)


def test_update_student_changes_email():
    students, uow = FakeStudents(), FakeUoW()
    v = uc.RegisterStudent(students, uow).execute(school_id="sch1", data=NewStudent(name="A", guardian_email="a@t.com"))
    out = uc.UpdateStudent(students, uow).execute(school_id="sch1", student_id=v.id, changes={"guardian_email": "novo@t.com"})
    assert out.guardian_email == "novo@t.com"


def test_list_children_reconciles_by_email():
    students, links, uow = FakeStudents(), FakeLinks(), FakeUoW()
    reg = uc.RegisterStudent(students, uow)
    reg.execute(school_id="sch1", data=NewStudent(name="Filho1", guardian_email="pai@t.com"))
    reg.execute(school_id="sch1", data=NewStudent(name="Filho2", guardian_email="pai@t.com"))
    reg.execute(school_id="sch1", data=NewStudent(name="Outro", guardian_email="outro@t.com"))
    views = uc.ListChildrenForParent(students, links, uow).execute(parent_id="p1", parent_email="PAI@t.com")
    assert sorted(v.name for v in views) == ["Filho1", "Filho2"]
    assert links.student_ids_for_parent("p1") == {v.id for v in views}
