import datetime as dt
from dataclasses import dataclass

from app.models.family_subscription import FamilySubStatus, FamilyPriceTier
from app.contexts.family.domain.subscription import FamilySubscription


@dataclass
class SubscriptionView:
    id: str
    parent_id: str
    school_id: str
    status: FamilySubStatus
    price_tier: FamilyPriceTier
    current_period: dt.date | None
    expires_at: dt.date | None

    @classmethod
    def of(cls, s: FamilySubscription) -> "SubscriptionView":
        return cls(
            id=s.id, parent_id=s.parent_id, school_id=s.school_id, status=s.status,
            price_tier=s.price_tier, current_period=s.current_period, expires_at=s.expires_at,
        )
