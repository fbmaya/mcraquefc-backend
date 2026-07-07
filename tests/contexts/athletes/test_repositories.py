from app.shared.domain.value_objects import Email
from app.contexts.athletes.domain.student import Student
from app.contexts.athletes.infrastructure.repositories import (
    SqlAlchemyStudentRepository, SqlAlchemyParentLinkRepository,
)


def _new(repo, school_id="sch1", email="pai@t.com", name="Lucas"):
    s = Student.register(id=repo.next_id(), school_id=school_id, name=name,
                         guardian_email=Email.parse(email))
    repo.add(s)
    return s


def test_add_and_get_roundtrip(db_session):
    repo = SqlAlchemyStudentRepository(db_session)
    s = _new(repo)
    db_session.commit()
    got = repo.get(s.id)
    assert got is not None
    assert got.name == "Lucas"
    assert got.guardian_email == Email.parse("pai@t.com")


def test_list_by_school_and_by_email(db_session):
    repo = SqlAlchemyStudentRepository(db_session)
    _new(repo, email="pai@t.com", name="A")
    _new(repo, email="pai@t.com", name="B")
    _new(repo, email="outro@t.com", name="C")
    db_session.commit()
    assert {s.name for s in repo.list_by_school("sch1")} == {"A", "B", "C"}
    assert {s.name for s in repo.list_by_guardian_email(Email.parse("PAI@t.com"))} == {"A", "B"}


def test_parent_links(db_session):
    students = SqlAlchemyStudentRepository(db_session)
    s = _new(students)
    db_session.commit()
    links = SqlAlchemyParentLinkRepository(db_session)
    assert links.student_ids_for_parent("p1") == set()
    links.link("p1", s.id)
    db_session.commit()
    assert links.student_ids_for_parent("p1") == {s.id}
