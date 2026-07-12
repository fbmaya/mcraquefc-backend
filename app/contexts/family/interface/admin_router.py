"""Gestão das assinaturas Family individuais (Caminho 2) — platform_admin.

O pacote da escola (Caminho 1) é gerido via License no /platform (family_included).
Aqui ficam só as assinaturas individuais, quando a escola não inclui Family."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.deps import require_platform_admin
from app.database import get_db
from app.models.user import User, UserRole
from app.models.school import School
from app.models.family_subscription import FamilySubStatus, FamilyPriceTier
from app.contexts.family.application import use_cases as uc
from app.contexts.family.interface import deps

router = APIRouter(prefix="/platform", tags=["platform-family"])


class SubscriptionCreate(BaseModel):
    # O admin identifica o responsável pelo e-mail (parents não são escopados por escola).
    parent_email: EmailStr
    price_tier: FamilyPriceTier = FamilyPriceTier.cheio
    current_period: dt.date | None = None
    expires_at: dt.date | None = None


class SubscriptionOut(BaseModel):
    id: str
    parent_id: str
    parent_email: str | None
    parent_name: str | None
    school_id: str
    status: FamilySubStatus
    price_tier: FamilyPriceTier
    current_period: dt.date | None
    expires_at: dt.date | None


def _out(view, db: Session) -> SubscriptionOut:
    """Enriquece a view com e-mail/nome do responsável (parents não vêm do domínio Family)."""
    u = db.get(User, view.parent_id)
    return SubscriptionOut(
        id=view.id, parent_id=view.parent_id,
        parent_email=u.email if u else None, parent_name=u.name if u else None,
        school_id=view.school_id, status=view.status, price_tier=view.price_tier,
        current_period=view.current_period, expires_at=view.expires_at,
    )


@router.get("/schools/{school_id}/family-subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(school_id: str, db: Session = Depends(get_db),
                       subs=Depends(deps.subscription_repo),
                       _: User = Depends(require_platform_admin)):
    return [_out(v, db) for v in uc.ListSubscriptions(subs).execute(school_id=school_id)]


@router.post("/schools/{school_id}/family-subscriptions", response_model=SubscriptionOut,
             status_code=status.HTTP_201_CREATED)
def create_subscription(school_id: str, body: SubscriptionCreate, db: Session = Depends(get_db),
                        subs=Depends(deps.subscription_repo), uow=Depends(deps.uow),
                        _: User = Depends(require_platform_admin)):
    if db.get(School, school_id) is None:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")
    parent = (
        db.query(User)
        .filter(func.lower(User.email) == body.parent_email.strip().lower(),
                User.role == UserRole.parent)
        .first()
    )
    if parent is None:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    try:
        view = uc.CreateSubscription(subs, uow).execute(
            parent_id=parent.id, school_id=school_id, price_tier=body.price_tier,
            current_period=body.current_period, expires_at=body.expires_at)
    except uc.SubscriptionAlreadyExists:
        raise HTTPException(status_code=409, detail="Já existe assinatura Family para este responsável nesta escola")
    return _out(view, db)


@router.delete("/family-subscriptions/{subscription_id}", response_model=SubscriptionOut)
def cancel_subscription(subscription_id: str, db: Session = Depends(get_db),
                        subs=Depends(deps.subscription_repo),
                        uow=Depends(deps.uow), _: User = Depends(require_platform_admin)):
    try:
        view = uc.CancelSubscription(subs, uow).execute(subscription_id=subscription_id)
    except uc.SubscriptionNotFound:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    return _out(view, db)
