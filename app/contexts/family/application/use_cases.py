import datetime as dt

from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.models.family_subscription import FamilyPriceTier
from app.contexts.family.domain.subscription import FamilySubscription
from app.contexts.family.domain.repositories import FamilySubscriptionRepository
from app.contexts.family.application.dtos import SubscriptionView


class SubscriptionAlreadyExists(DomainError):
    pass


class SubscriptionNotFound(DomainError):
    pass


class CreateSubscription:
    """Cria assinatura Family individual (Caminho 2) — ação do platform_admin."""

    def __init__(self, subs: FamilySubscriptionRepository, uow: UnitOfWork):
        self.subs, self.uow = subs, uow

    def execute(self, *, parent_id: str, school_id: str,
                price_tier: FamilyPriceTier = FamilyPriceTier.cheio,
                current_period: dt.date | None = None,
                expires_at: dt.date | None = None) -> SubscriptionView:
        if self.subs.active_for(parent_id, school_id) is not None:
            raise SubscriptionAlreadyExists("Já existe assinatura Family para este responsável nesta escola")
        sub = FamilySubscription.open(
            id=self.subs.next_id(), parent_id=parent_id, school_id=school_id,
            price_tier=price_tier, current_period=current_period, expires_at=expires_at,
        )
        self.subs.add(sub)
        self.uow.commit()
        return SubscriptionView.of(sub)


class CancelSubscription:
    def __init__(self, subs: FamilySubscriptionRepository, uow: UnitOfWork):
        self.subs, self.uow = subs, uow

    def execute(self, *, subscription_id: str) -> SubscriptionView:
        sub = self.subs.get(subscription_id)
        if sub is None:
            raise SubscriptionNotFound("Assinatura não encontrada")
        sub.cancel()
        self.subs.save(sub)
        self.uow.commit()
        return SubscriptionView.of(sub)


class ListSubscriptions:
    def __init__(self, subs: FamilySubscriptionRepository):
        self.subs = subs

    def execute(self, *, school_id: str) -> list[SubscriptionView]:
        return [SubscriptionView.of(s) for s in self.subs.list_by_school(school_id)]
