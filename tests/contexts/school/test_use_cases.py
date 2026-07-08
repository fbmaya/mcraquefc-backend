import pytest
from app.contexts.school.domain.school_class import SchoolClass
from app.contexts.school.domain.enrollment import Enrollment
from app.contexts.school.domain.repositories import (
    ClassRepository, EnrollmentRepository, StudentLookup,
)
from app.contexts.school.application.dtos import NewClass
from app.contexts.school.application import use_cases as uc


class FakeClasses(ClassRepository):
    def __init__(self):
        self.items: dict[str, SchoolClass] = {}
        self.enrolled: dict[str, list[str]] = {}
        self._seq = 0

    def add(self, c): self.items[c.id] = c
    def get(self, cid): return self.items.get(cid)
    def list_by_school(self, school_id): return [c for c in self.items.values() if c.school_id == school_id]
    def remove(self, c): self.items.pop(c.id, None)
    def active_student_ids(self, class_id): return list(self.enrolled.get(class_id, []))
    def next_id(self):
        self._seq += 1
        return f"c{self._seq}"


class FakeEnrollments(EnrollmentRepository):
    def __init__(self):
        self.rows: dict[tuple[str, str], Enrollment] = {}
        self._seq = 0

    def find(self, class_id, student_id): return self.rows.get((class_id, student_id))
    def create(self, id, class_id, student_id):
        self.rows[(class_id, student_id)] = Enrollment(id, class_id, student_id, True)
    def set_active(self, class_id, student_id, active):
        e = self.rows.get((class_id, student_id))
        if e:
            self.rows[(class_id, student_id)] = Enrollment(e.id, class_id, student_id, active)
    def next_id(self):
        self._seq += 1
        return f"e{self._seq}"


class FakeStudents(StudentLookup):
    def __init__(self, mapping: dict[str, str]):  # student_id -> school_id
        self.mapping = mapping
    def belongs_to_school(self, student_id, school_id):
        return self.mapping.get(student_id) == school_id


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def test_create_class_commits_and_returns_view():
    classes, uow = FakeClasses(), FakeUoW()
    view = uc.CreateClass(classes, uow).execute(
        school_id="sch1", data=NewClass(name="Sub-9 A", period="Manhã"))
    assert view.name == "Sub-9 A"
    assert view.period == "Manhã"
    assert view.student_ids == []
    assert uow.commits == 1
    assert classes.get(view.id) is not None


def test_list_classes_scoped_by_school():
    classes, uow = FakeClasses(), FakeUoW()
    reg = uc.CreateClass(classes, uow)
    reg.execute(school_id="sch1", data=NewClass(name="A"))
    reg.execute(school_id="sch2", data=NewClass(name="B"))
    views = uc.ListClasses(classes).execute(school_id="sch1")
    assert [v.name for v in views] == ["A"]


def test_update_class_wrong_school_raises():
    classes, uow = FakeClasses(), FakeUoW()
    v = uc.CreateClass(classes, uow).execute(school_id="sch1", data=NewClass(name="A"))
    with pytest.raises(uc.ClassNotFound):
        uc.UpdateClass(classes, uow).execute(school_id="OUTRA", class_id=v.id, changes={"name": "X"})


def test_update_class_changes_period():
    classes, uow = FakeClasses(), FakeUoW()
    v = uc.CreateClass(classes, uow).execute(school_id="sch1", data=NewClass(name="A", period="Manhã"))
    out = uc.UpdateClass(classes, uow).execute(school_id="sch1", class_id=v.id, changes={"period": "Noite"})
    assert out.period == "Noite"


def test_enroll_student_creates_and_reflects_in_view():
    classes, enrolls, uow = FakeClasses(), FakeEnrollments(), FakeUoW()
    students = FakeStudents({"stu1": "sch1"})
    v = uc.CreateClass(classes, uow).execute(school_id="sch1", data=NewClass(name="A"))
    # fake ClassRepository.active_student_ids reads classes.enrolled; keep them in sync here
    en = uc.EnrollStudent(classes, enrolls, students, uow)
    out = en.execute(school_id="sch1", class_id=v.id, student_id="stu1")
    assert out.class_id == v.id and out.student_id == "stu1" and out.active is True
    assert enrolls.find(v.id, "stu1").active is True


def test_enroll_rejects_student_from_another_school():
    classes, enrolls, uow = FakeClasses(), FakeEnrollments(), FakeUoW()
    students = FakeStudents({"stu1": "OUTRA"})
    v = uc.CreateClass(classes, uow).execute(school_id="sch1", data=NewClass(name="A"))
    with pytest.raises(uc.StudentNotFound):
        uc.EnrollStudent(classes, enrolls, students, uow).execute(
            school_id="sch1", class_id=v.id, student_id="stu1")


def test_enroll_reactivates_existing():
    classes, enrolls, uow = FakeClasses(), FakeEnrollments(), FakeUoW()
    students = FakeStudents({"stu1": "sch1"})
    v = uc.CreateClass(classes, uow).execute(school_id="sch1", data=NewClass(name="A"))
    en = uc.EnrollStudent(classes, enrolls, students, uow)
    first = en.execute(school_id="sch1", class_id=v.id, student_id="stu1")
    enrolls.set_active(v.id, "stu1", False)
    second = en.execute(school_id="sch1", class_id=v.id, student_id="stu1")
    assert second.id == first.id  # same enrollment reactivated, not a new one
    assert second.active is True


def test_unenroll_deactivates():
    classes, enrolls, uow = FakeClasses(), FakeEnrollments(), FakeUoW()
    students = FakeStudents({"stu1": "sch1"})
    v = uc.CreateClass(classes, uow).execute(school_id="sch1", data=NewClass(name="A"))
    uc.EnrollStudent(classes, enrolls, students, uow).execute(school_id="sch1", class_id=v.id, student_id="stu1")
    uc.UnenrollStudent(classes, enrolls, uow).execute(school_id="sch1", class_id=v.id, student_id="stu1")
    assert enrolls.find(v.id, "stu1").active is False
