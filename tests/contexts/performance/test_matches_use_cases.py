import datetime as dt
import pytest
from app.contexts.performance.domain.match import Match
from app.contexts.performance.domain.repositories import MatchRepository
from app.contexts.performance.application.matches_dtos import NewMatch, NewMatchStat
from app.contexts.performance.application import matches_use_cases as uc


class FakeMatches(MatchRepository):
    def __init__(self):
        self.items: dict[str, Match] = {}
        self._m = 0
        self._s = 0

    def add(self, m): self.items[m.id] = m
    def save(self, m): self.items[m.id] = m
    def get(self, mid): return self.items.get(mid)
    def list_by_school(self, school_id): return [m for m in self.items.values() if m.school_id == school_id]
    def list_by_student(self, student_id):
        return [m for m in self.items.values()
                if any(st.student_id == student_id for st in m.stats)]

    def remove(self, m): self.items.pop(m.id, None)
    def next_id(self):
        self._m += 1
        return f"m{self._m}"
    def next_stat_id(self):
        self._s += 1
        return f"s{self._s}"


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def _new(**kw):
    base = dict(date=dt.date(2026, 6, 1), opponent="Rival FC")
    base.update(kw)
    return NewMatch(**base)


def test_create_match_with_stats_returns_view():
    repo, uow = FakeMatches(), FakeUoW()
    view = uc.CreateMatch(repo, uow).execute(school_id="sch1", data=_new(
        score_us=4, stats=[NewMatchStat(student_id="stu1", goals=2), NewMatchStat(student_id="stu2")]))
    assert view.opponent == "Rival FC"
    assert view.score_us == 4
    assert len(view.stats) == 2
    assert {s.student_id for s in view.stats} == {"stu1", "stu2"}
    assert all(s.id for s in view.stats)  # stat ids assigned
    assert uow.commits == 1


def test_create_rejects_empty_opponent():
    repo, uow = FakeMatches(), FakeUoW()
    with pytest.raises(Exception):
        uc.CreateMatch(repo, uow).execute(school_id="sch1", data=_new(opponent="  "))


def test_list_matches_scoped_by_school():
    repo, uow = FakeMatches(), FakeUoW()
    c = uc.CreateMatch(repo, uow)
    c.execute(school_id="sch1", data=_new(opponent="A"))
    c.execute(school_id="sch2", data=_new(opponent="B"))
    views = uc.ListMatches(repo).execute(school_id="sch1")
    assert [v.opponent for v in views] == ["A"]


def test_update_match_wrong_school_raises():
    repo, uow = FakeMatches(), FakeUoW()
    v = uc.CreateMatch(repo, uow).execute(school_id="sch1", data=_new())
    with pytest.raises(uc.MatchNotFound):
        uc.UpdateMatch(repo, uow).execute(school_id="OUTRA", match_id=v.id, changes={"opponent": "X"})


def test_update_match_changes_scalars_only():
    repo, uow = FakeMatches(), FakeUoW()
    v = uc.CreateMatch(repo, uow).execute(school_id="sch1", data=_new(
        stats=[NewMatchStat(student_id="stu1")]))
    out = uc.UpdateMatch(repo, uow).execute(school_id="sch1", match_id=v.id,
                                            changes={"opponent": "Novo FC", "score_us": 3})
    assert out.opponent == "Novo FC"
    assert out.score_us == 3
    assert len(out.stats) == 1  # stats untouched


def test_delete_match():
    repo, uow = FakeMatches(), FakeUoW()
    v = uc.CreateMatch(repo, uow).execute(school_id="sch1", data=_new())
    uc.DeleteMatch(repo, uow).execute(school_id="sch1", match_id=v.id)
    assert repo.get(v.id) is None
