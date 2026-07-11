import datetime as dt
import pytest
from app.shared.domain.errors import ValidationError
from app.models.family_subscription import FamilySubStatus, FamilyPriceTier
from app.contexts.family.domain.subscription import FamilySubscription


def make(**kw):
    base = dict(id="f1", parent_id="p1", school_id="s1")
    base.update(kw)
    return FamilySubscription.open(**base)


def test_open_requires_parent_and_school():
    with pytest.raises(ValidationError):
        make(parent_id="")
    with pytest.raises(ValidationError):
        make(school_id="")


def test_open_starts_active_cheio():
    s = make()
    assert s.status == FamilySubStatus.active and s.price_tier == FamilyPriceTier.cheio


def test_cancel():
    s = make()
    s.cancel()
    assert s.status == FamilySubStatus.cancelled


def test_covers_no_expiry_when_active():
    assert make().covers(dt.date(2026, 7, 11)) is True


def test_covers_false_when_expired_sem_carencia():
    s = make(expires_at=dt.date(2026, 6, 30))
    assert s.covers(dt.date(2026, 7, 1)) is False   # venceu ontem, sem carência
    assert s.covers(dt.date(2026, 6, 30)) is True    # último dia ainda cobre


def test_covers_false_when_not_active():
    s = make(expires_at=dt.date(2026, 12, 31))
    s.cancel()
    assert s.covers(dt.date(2026, 7, 11)) is False
