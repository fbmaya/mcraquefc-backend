import datetime as dt
import pytest
from app.shared.domain.errors import ValidationError
from app.contexts.assessment.domain.evaluation import Evaluation


def make(skills=None, **kw):
    base = dict(id="e1", student_id="stu1", date=dt.date(2026, 6, 1), skills=skills or {})
    base.update(kw)
    return Evaluation.register(**base)


def test_register_requires_student():
    with pytest.raises(ValidationError):
        make(student_id="")


def test_register_sets_skills():
    e = make(skills={"passing": 8.0, "finishing": 6.0}, evaluated_by="coach1")
    assert e.passing == 8.0 and e.finishing == 6.0
    assert e.dribbling is None
    assert e.evaluated_by == "coach1"


def test_summary_axes_average_present_skills():
    e = make(skills={"passing": 8.0, "finishing": 6.0, "dribbling": 7.0, "speed": 9.0, "stamina": 5.0})
    assert e.technique == 7.0           # (8+6+7)/3
    assert e.physical == 7.0            # (9+5)/2  (agility None ignored)
    assert e.tactical is None           # positioning/decision both None
    assert e.overall == 7.0             # (8+6+7+9+5)/5


def test_overall_none_when_no_skills():
    assert make().overall is None
