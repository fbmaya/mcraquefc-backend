import datetime as dt
import pytest
from app.shared.domain.errors import ValidationError
from app.contexts.attendance.domain.session import AttendanceSession, AttendanceRecordLine


def make(**kw):
    base = dict(id="a1", class_id="cls1", date=dt.date(2026, 6, 1), records=[])
    base.update(kw)
    return AttendanceSession.register(**base)


def test_register_requires_class():
    with pytest.raises(ValidationError):
        make(class_id="")


def test_register_sets_fields_and_defaults():
    s = make(notes="treino")
    assert s.class_id == "cls1"
    assert s.date == dt.date(2026, 6, 1)
    assert s.notes == "treino"
    assert s.records == []


def test_register_keeps_records():
    r = AttendanceRecordLine(id="r1", student_id="stu1", present=True)
    s = make(records=[r])
    assert s.records == [r]
    assert s.records[0].present is True
