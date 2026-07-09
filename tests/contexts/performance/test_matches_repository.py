import datetime as dt
import uuid
from app.database import SessionLocal
from app.models.school import School
from app.models.student import Student as StudentORM
from app.models.match import MatchStat as MatchStatORM
from app.contexts.performance.domain.match import Match, MatchStatLine
from app.contexts.performance.infrastructure.repositories import SqlAlchemyMatchRepository


def _seed(db):
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    stu = StudentORM(id=str(uuid.uuid4()), school_id=school.id, name="Lucas", guardian_email="p@t.com")
    db.add(stu)
    db.commit()
    return school.id, stu.id


def _match(repo, school_id, stu_id, opponent="Rival FC"):
    return Match.register(
        id=repo.next_id(), school_id=school_id, date=dt.date(2026, 6, 1), opponent=opponent,
        score_us=4, stats=[MatchStatLine(id=repo.next_stat_id(), student_id=stu_id, goals=2)],
    )


def test_create_with_stats_persists(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyMatchRepository(db_session)
    m = _match(repo, school_id, stu_id)
    repo.add(m)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = SqlAlchemyMatchRepository(fresh).get(m.id)
        assert got is not None and got.opponent == "Rival FC" and got.score_us == 4
        assert len(got.stats) == 1 and got.stats[0].goals == 2 and got.stats[0].student_id == stu_id
    finally:
        fresh.close()


def test_update_scalar_persists_from_fresh_session(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyMatchRepository(db_session)
    m = _match(repo, school_id, stu_id)
    repo.add(m)
    db_session.commit()
    m.change_fields(opponent="Novo FC", score_us=1)
    repo.save(m)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = SqlAlchemyMatchRepository(fresh).get(m.id)
        assert got.opponent == "Novo FC" and got.score_us == 1
        assert len(got.stats) == 1  # save must not drop stats
    finally:
        fresh.close()


def test_list_by_school_scoped_and_ordered(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyMatchRepository(db_session)
    older = Match.register(id=repo.next_id(), school_id=school_id, date=dt.date(2026, 1, 1),
                           opponent="Older", stats=[])
    newer = Match.register(id=repo.next_id(), school_id=school_id, date=dt.date(2026, 9, 1),
                           opponent="Newer", stats=[])
    other = Match.register(id=repo.next_id(), school_id="OTHER", date=dt.date(2026, 6, 1),
                           opponent="Other", stats=[])
    for x in (older, newer, other):
        repo.add(x)
    db_session.commit()
    got = repo.list_by_school(school_id)
    assert [m.opponent for m in got] == ["Newer", "Older"]  # date desc


def test_remove_deletes_match_and_its_stats(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyMatchRepository(db_session)
    m = _match(repo, school_id, stu_id)
    repo.add(m)
    db_session.commit()
    assert db_session.query(MatchStatORM).filter(MatchStatORM.match_id == m.id).count() == 1
    repo.remove(m)
    db_session.commit()
    assert repo.get(m.id) is None
    assert db_session.query(MatchStatORM).filter(MatchStatORM.match_id == m.id).count() == 0  # no orphans
