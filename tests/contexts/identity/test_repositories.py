import uuid
from app.database import SessionLocal
from app.models.school import School
from app.models.user import User as UserORM, UserRole
from app.models.student import Student as StudentORM
from app.contexts.identity.domain.user import User
from app.contexts.identity.infrastructure.repositories import (
    SqlAlchemyUserRepository, SqlAlchemyParentLinkRepository,
)


def test_add_get_and_lookups(db_session):
    repo = SqlAlchemyUserRepository(db_session)
    u = User.register_parent(id=repo.next_id(), name="Mãe", email="Mae@T.com", hashed_password="h")
    repo.add(u)
    db_session.commit()
    fresh = SessionLocal()
    try:
        r = SqlAlchemyUserRepository(fresh)
        assert r.get(u.id).email == "Mae@T.com"
        assert r.get_by_email("Mae@T.com") is not None          # exata
        assert r.get_by_email("mae@t.com") is None               # exata não bate case
        assert r.find_by_email_ci("mae@t.com").id == u.id        # case-insensitive
        assert r.email_exists("Mae@T.com") is True
        assert r.email_exists("nope@t.com") is False
    finally:
        fresh.close()


def test_save_updates_google_sub(db_session):
    repo = SqlAlchemyUserRepository(db_session)
    u = User.register_parent(id=repo.next_id(), name="A", email="a@t.com", hashed_password="h")
    repo.add(u)
    db_session.commit()
    u.link_google("sub-123")
    repo.save(u)
    db_session.commit()
    fresh = SessionLocal()
    try:
        assert SqlAlchemyUserRepository(fresh).get(u.id).google_sub == "sub-123"
    finally:
        fresh.close()


def test_parent_link_reconcile_queries(db_session):
    # aluno com guardian_email + responsável
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db_session.add(school)
    stu = StudentORM(id=str(uuid.uuid4()), school_id=school.id, name="Filho", guardian_email="MAE@t.com")
    db_session.add(stu)
    parent = UserORM(id=str(uuid.uuid4()), school_id=None, name="Mãe", email="mae@t.com",
                     hashed_password="h", role=UserRole.parent)
    db_session.add(parent)
    db_session.commit()

    links = SqlAlchemyParentLinkRepository(db_session)
    # match case-insensitive do guardian_email
    assert links.student_ids_for_guardian_email("mae@t.com") == [stu.id]
    assert links.linked_student_ids(parent.id) == set()
    links.add_link(links.next_id(), parent.id, stu.id)
    db_session.commit()
    assert links.linked_student_ids(parent.id) == {stu.id}
