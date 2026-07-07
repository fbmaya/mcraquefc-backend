import datetime as dt
import pytest
from app.shared.domain.value_objects import Email
from app.shared.domain.errors import ValidationError
from app.contexts.athletes.domain.student import Student, matches_guardian


def make(**kw):
    base = dict(id="s1", school_id="sch1", name="Lucas", guardian_email=Email.parse("pai@t.com"))
    base.update(kw)
    return Student.register(**base)


def test_register_requires_guardian_email():
    with pytest.raises(ValidationError):
        Student.register(id="s1", school_id="sch1", name="Lucas", guardian_email=None)


def test_register_requires_name():
    with pytest.raises(ValidationError):
        make(name="   ")


def test_register_sets_fields():
    s = make(position="Ponta", birth_date=dt.date(2016, 3, 1))
    assert s.name == "Lucas"
    assert s.guardian_email.value == "pai@t.com"
    assert s.position == "Ponta"


def test_change_updates_only_given_fields():
    s = make()
    s.change(position="Goleiro", guardian_email=Email.parse("novo@t.com"))
    assert s.position == "Goleiro"
    assert s.guardian_email.value == "novo@t.com"
    assert s.name == "Lucas"


def test_matches_guardian_is_case_insensitive():
    s = make()
    assert matches_guardian(s, Email.parse("PAI@T.COM")) is True
    assert matches_guardian(s, Email.parse("outro@t.com")) is False
