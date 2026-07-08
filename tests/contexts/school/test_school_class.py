import pytest
from app.shared.domain.errors import ValidationError
from app.contexts.school.domain.school_class import SchoolClass


def make(**kw):
    base = dict(id="c1", school_id="sch1", name="Sub-9 A")
    base.update(kw)
    return SchoolClass.register(**base)


def test_register_requires_name():
    with pytest.raises(ValidationError):
        make(name="   ")


def test_register_sets_fields():
    c = make(period="Manhã", age_group="Sub-9", coach_id="co1")
    assert c.name == "Sub-9 A"
    assert c.period == "Manhã"
    assert c.age_group == "Sub-9"
    assert c.coach_id == "co1"
    assert c.schedule is None


def test_change_updates_only_given_fields():
    c = make(period="Manhã")
    c.change(period="Noite", schedule="Seg/Qua 19h")
    assert c.period == "Noite"
    assert c.schedule == "Seg/Qua 19h"
    assert c.name == "Sub-9 A"


def test_change_ignores_unknown_fields():
    c = make()
    c.change(school_id="HACK", id="HACK")
    assert c.school_id == "sch1"
    assert c.id == "c1"
