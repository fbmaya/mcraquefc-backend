import datetime as dt
from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError
# Vocabulário compartilhado (str-enums sem comportamento): reusados do model.
from app.models.family_subscription import FamilySubStatus, FamilyPriceTier


@dataclass(eq=False)
class FamilySubscription(AggregateRoot):
    """Assinatura Family individual, por (responsável, escolinha).

    Cobre todos os filhos ativos do responsável naquela escola (Caminho 2)."""
    parent_id: str = ""
    school_id: str = ""
    status: FamilySubStatus = FamilySubStatus.active
    price_tier: FamilyPriceTier = FamilyPriceTier.cheio
    current_period: dt.date | None = None
    expires_at: dt.date | None = None
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None

    @classmethod
    def open(cls, *, id: str, parent_id: str, school_id: str,
             price_tier: FamilyPriceTier = FamilyPriceTier.cheio,
             current_period: dt.date | None = None,
             expires_at: dt.date | None = None) -> "FamilySubscription":
        if not parent_id:
            raise ValidationError("Responsável é obrigatório")
        if not school_id:
            raise ValidationError("Escolinha é obrigatória")
        return cls(id=id, parent_id=parent_id, school_id=school_id, status=FamilySubStatus.active,
                   price_tier=price_tier, current_period=current_period, expires_at=expires_at)

    def cancel(self) -> None:
        self.status = FamilySubStatus.cancelled

    def covers(self, today: dt.date) -> bool:
        """Cobre o acesso hoje? Ativa e ainda não vencida (sem carência)."""
        if self.status != FamilySubStatus.active:
            return False
        return self.expires_at is None or self.expires_at >= today
