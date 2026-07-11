from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class FamilySubStatus(str, enum.Enum):
    active    = "active"
    overdue   = "overdue"
    cancelled = "cancelled"
    pending   = "pending"


class FamilyPriceTier(str, enum.Enum):
    cheio        = "cheio"         # R$25
    pontualidade = "pontualidade"  # R$20
    promo        = "promo"         # R$15


class FamilySubscription(Base):
    """Assinatura Family INDIVIDUAL, por (responsável, escolinha).

    Só existe no Caminho 2 (escola sem pacote Family). Cobre todos os filhos
    ativos do responsável naquela escola. O Caminho 1 (pacote da escola) é
    derivado de License.family_included e NÃO gera linha aqui."""

    __tablename__ = "family_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parent_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"), index=True)
    status: Mapped[FamilySubStatus] = mapped_column(Enum(FamilySubStatus), default=FamilySubStatus.active)
    price_tier: Mapped[FamilyPriceTier] = mapped_column(Enum(FamilyPriceTier), default=FamilyPriceTier.cheio)
    current_period: Mapped[date | None] = mapped_column(Date)  # mês de referência
    expires_at: Mapped[date | None] = mapped_column(Date)      # fim do período pago
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    parent: Mapped["User"] = relationship()
    school: Mapped["School"] = relationship()
