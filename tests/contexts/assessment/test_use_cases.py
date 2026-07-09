import datetime as dt
import pytest
from app.contexts.assessment.domain.evaluation import Evaluation
from app.contexts.assessment.domain.repositories import EvaluationRepository
from app.contexts.assessment.application.evaluation_dtos import NewEvaluation
from app.contexts.assessment.application import evaluation_use_cases as uc


class FakeEvaluations(EvaluationRepository):
    def __init__(self, students: dict[str, str] | None = None):
        self.items: dict[str, Evaluation] = {}
        self.students = students or {}   # student_id -> school_id
        self._n = 0

    def add(self, e): self.items[e.id] = e
    def get(self, eid): return self.items.get(eid)

    def list_by_school(self, school_id, student_id=None):
        out = [e for e in self.items.values() if self.students.get(e.student_id) == school_id]
        if student_id:
            out = [e for e in out if e.student_id == student_id]
        return out

    def remove(self, e): self.items.pop(e.id, None)
    def student_belongs_to_school(self, student_id, school_id): return self.students.get(student_id) == school_id

    def next_id(self):
        self._n += 1
        return f"e{self._n}"


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def _new(**kw):
    base = dict(student_id="stu1", date=dt.date(2026, 6, 1))
    base.update(kw)
    return NewEvaluation(**base)


def test_create_evaluation_records_evaluator_and_view():
    repo = FakeEvaluations(students={"stu1": "sch1"})
    uow = FakeUoW()
    view = uc.CreateEvaluation(repo, uow).execute(
        school_id="sch1", evaluated_by="coach1", data=_new(skills={"passing": 8.0}))
    assert view.student_id == "stu1" and view.evaluated_by == "coach1" and view.passing == 8.0
    assert uow.commits == 1


def test_create_rejects_foreign_student():
    repo = FakeEvaluations(students={"stu1": "OUTRA"})
    with pytest.raises(uc.StudentNotFound):
        uc.CreateEvaluation(repo, FakeUoW()).execute(school_id="sch1", evaluated_by="c", data=_new())


def test_list_scoped_by_school_and_student():
    repo = FakeEvaluations(students={"stu1": "sch1", "stu2": "sch1", "stu3": "sch2"})
    c = lambda sid, sch: uc.CreateEvaluation(repo, FakeUoW()).execute(
        school_id=sch, evaluated_by="c", data=_new(student_id=sid))
    c("stu1", "sch1"); c("stu2", "sch1"); c("stu3", "sch2")
    assert len(uc.ListEvaluations(repo).execute(school_id="sch1")) == 2
    only1 = uc.ListEvaluations(repo).execute(school_id="sch1", student_id="stu1")
    assert [e.student_id for e in only1] == ["stu1"]


def test_delete_evaluation():
    repo = FakeEvaluations(students={"stu1": "sch1"})
    v = uc.CreateEvaluation(repo, FakeUoW()).execute(school_id="sch1", evaluated_by="c", data=_new())
    uc.DeleteEvaluation(repo, FakeUoW()).execute(school_id="sch1", evaluation_id=v.id)
    assert repo.get(v.id) is None


def test_delete_wrong_school_raises():
    repo = FakeEvaluations(students={"stu1": "sch1"})
    v = uc.CreateEvaluation(repo, FakeUoW()).execute(school_id="sch1", evaluated_by="c", data=_new())
    with pytest.raises(uc.EvaluationNotFound):
        uc.DeleteEvaluation(repo, FakeUoW()).execute(school_id="OUTRA", evaluation_id=v.id)
