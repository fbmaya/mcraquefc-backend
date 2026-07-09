import datetime as dt
import pytest
from app.shared.domain.errors import ValidationError
from app.contexts.performance.domain.match import Match, MatchStatLine


def make(**kw):
    base = dict(id="m1", school_id="sch1", date=dt.date(2026, 6, 1), opponent="Rival FC", stats=[])
    base.update(kw)
    return Match.register(**base)


def test_register_requires_opponent():
    with pytest.raises(ValidationError):
        make(opponent="  ")


def test_register_sets_fields_and_defaults():
    m = make(score_us=4, score_them=1, category="Sub-9")
    assert m.opponent == "Rival FC"
    assert m.home is True
    assert m.score_us == 4
    assert m.stats == []


def test_register_keeps_stats():
    s = MatchStatLine(id="s1", student_id="stu1", goals=2)
    m = make(stats=[s])
    assert m.stats == [s]
    assert m.stats[0].goals == 2


def test_change_fields_updates_only_scalars():
    m = make()
    m.change_fields(opponent="Novo FC", score_us=3, home=False)
    assert m.opponent == "Novo FC"
    assert m.score_us == 3
    assert m.home is False
    assert m.date == dt.date(2026, 6, 1)


def test_change_fields_ignores_unknown():
    m = make()
    m.change_fields(school_id="HACK", id="HACK", stats=["nope"])
    assert m.school_id == "sch1"
    assert m.id == "m1"
    assert m.stats == []
