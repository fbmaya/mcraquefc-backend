import datetime as dt
import pytest
from app.shared.domain.errors import ValidationError
from app.models.license import PlanType, LicenseStatus
from app.contexts.platform.domain.tenant import School


def test_open_requires_name():
    with pytest.raises(ValidationError):
        School.open(id="s1", name="  ", license_id="l1")


def test_open_creates_trial_active_license():
    s = School.open(id="s1", name="Escolinha X", license_id="l1")
    assert s.name == "Escolinha X" and s.active is True
    assert s.license.plan == PlanType.trial and s.license.status == LicenseStatus.active
    assert s.license.max_students == 30 and s.license.max_coaches == 2


def test_change_details_scalars_only():
    s = School.open(id="s1", name="X", license_id="l1")
    s.change_details(name="Novo", primary_color="#fff", id="HACK")
    assert s.name == "Novo" and s.primary_color == "#fff" and s.id == "s1"


def test_apply_license_syncs_active_on_suspend():
    s = School.open(id="s1", name="X", license_id="l1")
    s.apply_license(license_id="ignored", status=LicenseStatus.suspended, max_students=100)
    assert s.license.status == LicenseStatus.suspended
    assert s.license.max_students == 100
    assert s.active is False  # sincronizado


def test_apply_license_creates_when_missing():
    s = School.open(id="s1", name="X", license_id="l1")
    s.license = None
    s.apply_license(license_id="l2", plan=PlanType.pro, expires_at=dt.date(2027, 1, 1))
    assert s.license is not None and s.license.id == "l2" and s.license.plan == PlanType.pro
    assert s.active is True  # default status active
