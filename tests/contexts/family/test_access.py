import datetime as dt
from app.contexts.family.domain.subscription import FamilySubscription
from app.contexts.family.domain.repositories import (
    FamilySubscriptionRepository, FamilyAccessReader, StudentAccessInfo,
)
from app.contexts.family.application.access import CheckFamilyAccess

TODAY = dt.date(2026, 7, 11)


class FakeSubs(FamilySubscriptionRepository):
    def __init__(self):
        self.items: dict[str, FamilySubscription] = {}
        self._n = 0

    def next_id(self):
        self._n += 1
        return f"f{self._n}"

    def add(self, s): self.items[s.id] = s
    def save(self, s): self.items[s.id] = s
    def get(self, sid): return self.items.get(sid)

    def active_for(self, parent_id, school_id):
        from app.models.family_subscription import FamilySubStatus
        return next((s for s in self.items.values()
                     if s.parent_id == parent_id and s.school_id == school_id
                     and s.status != FamilySubStatus.cancelled), None)

    def list_by_school(self, school_id):
        return [s for s in self.items.values() if s.school_id == school_id]


class FakeReader(FamilyAccessReader):
    def __init__(self, *, linked=True, student=StudentAccessInfo(True, "s1"), included=False):
        self._linked, self._student, self._included = linked, student, included

    def is_linked(self, parent_id, student_id): return self._linked
    def student_access_info(self, student_id): return self._student
    def school_family_included(self, school_id): return self._included


def _check(subs, reader):
    return CheckFamilyAccess(subs, reader).execute(parent_id="p1", student_id="stu1", today=TODAY)


def test_denied_when_not_linked():
    assert _check(FakeSubs(), FakeReader(linked=False)) is False


def test_denied_when_student_inactive():
    assert _check(FakeSubs(), FakeReader(student=StudentAccessInfo(False, "s1"))) is False


def test_denied_when_student_missing():
    assert _check(FakeSubs(), FakeReader(student=None)) is False


def test_allowed_via_school_package():
    # Caminho 1: escola com Family incluso → libera sem assinatura
    assert _check(FakeSubs(), FakeReader(included=True)) is True


def test_allowed_via_individual_subscription():
    subs = FakeSubs()
    subs.add(FamilySubscription.open(id="f1", parent_id="p1", school_id="s1"))
    assert _check(subs, FakeReader(included=False)) is True


def test_denied_when_subscription_other_school():
    subs = FakeSubs()
    subs.add(FamilySubscription.open(id="f1", parent_id="p1", school_id="OUTRA"))
    # aluno está na escola s1; assinatura é de OUTRA → não cobre
    assert _check(subs, FakeReader(included=False)) is False


def test_denied_when_subscription_expired():
    subs = FakeSubs()
    subs.add(FamilySubscription.open(id="f1", parent_id="p1", school_id="s1",
                                     expires_at=dt.date(2026, 6, 30)))
    assert _check(subs, FakeReader(included=False)) is False


def test_denied_when_no_path():
    assert _check(FakeSubs(), FakeReader(included=False)) is False
