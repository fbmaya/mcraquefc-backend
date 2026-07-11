import pytest
from app.models.family_subscription import FamilySubStatus
from app.contexts.family.application import use_cases as uc
from tests.contexts.family.test_access import FakeSubs


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def test_create_subscription():
    subs, uow = FakeSubs(), FakeUoW()
    v = uc.CreateSubscription(subs, uow).execute(parent_id="p1", school_id="s1")
    assert v.parent_id == "p1" and v.status == FamilySubStatus.active
    assert uow.commits == 1


def test_create_rejects_duplicate_active():
    subs, uow = FakeSubs(), FakeUoW()
    uc.CreateSubscription(subs, uow).execute(parent_id="p1", school_id="s1")
    with pytest.raises(uc.SubscriptionAlreadyExists):
        uc.CreateSubscription(subs, uow).execute(parent_id="p1", school_id="s1")


def test_create_allowed_after_cancel():
    subs, uow = FakeSubs(), FakeUoW()
    v = uc.CreateSubscription(subs, uow).execute(parent_id="p1", school_id="s1")
    uc.CancelSubscription(subs, uow).execute(subscription_id=v.id)
    # cancelada não bloqueia nova
    v2 = uc.CreateSubscription(subs, uow).execute(parent_id="p1", school_id="s1")
    assert v2.id != v.id


def test_cancel_missing_raises():
    with pytest.raises(uc.SubscriptionNotFound):
        uc.CancelSubscription(FakeSubs(), FakeUoW()).execute(subscription_id="nope")


def test_list_by_school():
    subs, uow = FakeSubs(), FakeUoW()
    uc.CreateSubscription(subs, uow).execute(parent_id="p1", school_id="s1")
    uc.CreateSubscription(subs, uow).execute(parent_id="p2", school_id="s1")
    uc.CreateSubscription(subs, uow).execute(parent_id="p3", school_id="s2")
    assert len(uc.ListSubscriptions(subs).execute(school_id="s1")) == 2
