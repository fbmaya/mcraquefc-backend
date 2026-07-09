import datetime as dt
import uuid
from app.database import SessionLocal
from app.models.school import School
from app.models.student import Student as StudentORM
from app.contexts.assessment.domain.evaluation import Evaluation
from app.contexts.assessment.infrastructure.repositories import SqlAlchemyEvaluationRepository


def _seed(db):
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    stu = StudentORM(id=str(uuid.uuid4()), school_id=school.id, name="Lucas", guardian_email="p@t.com")
    db.add(stu)
    db.commit()
    return school.id, stu.id


def _eval(repo, stu_id, date=dt.date(2026, 6, 1), skills=None):
    return Evaluation.register(id=repo.next_id(), student_id=stu_id, date=date,
                               skills=skills or {"passing": 8.0, "finishing": 6.0}, evaluated_by="coach1")


def test_create_persists_skills_and_computes_axes(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyEvaluationRepository(db_session)
    e = _eval(repo, stu_id, skills={"passing": 8.0, "finishing": 6.0, "dribbling": 7.0})
    repo.add(e)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = SqlAlchemyEvaluationRepository(fresh).get(e.id)
        assert got is not None and got.passing == 8.0 and got.evaluated_by == "coach1"
        assert got.technique == 7.0  # (8+6+7)/3
        assert got.created_at is not None
    finally:
        fresh.close()


def test_list_by_school_scoped_and_ordered(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyEvaluationRepository(db_session)
    for x in (_eval(repo, stu_id, dt.date(2026, 1, 1)), _eval(repo, stu_id, dt.date(2026, 9, 1))):
        repo.add(x)
    db_session.commit()
    got = repo.list_by_school(school_id)
    assert [e.date for e in got] == [dt.date(2026, 9, 1), dt.date(2026, 1, 1)]  # date desc


def test_remove(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyEvaluationRepository(db_session)
    e = _eval(repo, stu_id)
    repo.add(e)
    db_session.commit()
    repo.remove(e)
    db_session.commit()
    assert repo.get(e.id) is None


def test_student_belongs_to_school(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyEvaluationRepository(db_session)
    assert repo.student_belongs_to_school(stu_id, school_id) is True
    assert repo.student_belongs_to_school(stu_id, "OUTRA") is False
