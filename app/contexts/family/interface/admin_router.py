"""Gestão das assinaturas Family individuais (Caminho 2) — platform_admin.

O pacote da escola (Caminho 1) é gerido via License no /platform (family_included).
Aqui ficam só as assinaturas individuais, quando a escola não inclui Family."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
    parent_id: str
    price_tier: FamilyPriceTier = FamilyPriceTier.cheio
    current_period: dt.date | None = None
    expires_at: dt.date | None = None


class SubscriptionOut(BaseModel):
    id: str
    parent_id: str
    school_id: str
    status: FamilySubStatus
    price_tier: FamilyPriceTier
    current_period: dt.date | None
    expires_at: dt.date | None

    model_config = {"from_attributes": True}


@router.get("/schools/{school_id}/family-subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(school_id: str, subs=Depends(deps.subscription_repo),
                       _: User = Depends(require_platform_admin)):
    return uc.ListSubscriptions(subs).execute(school_id=school_id)


@router.post("/schools/{school_id}/family-subscriptions", response_model=SubscriptionOut,
             status_code=status.HTTP_201_CREATED)
def create_subscription(school_id: str, body: SubscriptionCreate, db: Session = Depends(get_db),
                        subs=Depends(deps.subscription_repo), uow=Depends(deps.uow),
                        _: User = Depends(require_platform_admin)):
    if db.get(School, school_id) is None:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")
    parent = db.get(User, body.parent_id)
    if parent is None or parent.role != UserRole.parent:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    try:
        return uc.CreateSubscription(subs, uow).execute(
            parent_id=body.parent_id, school_id=school_id, price_tier=body.price_tier,
            current_period=body.current_period, expires_at=body.expires_at)
    except uc.SubscriptionAlreadyExists:
        raise HTTPException(status_code=409, detail="Já existe assinatura Family para este responsável nesta escola")


@router.delete("/family-subscriptions/{subscription_id}", response_model=SubscriptionOut)
def cancel_subscription(subscription_id: str, subs=Depends(deps.subscription_repo),
                        uow=Depends(deps.uow), _: User = Depends(require_platform_admin)):
    try:
        return uc.CancelSubscription(subs, uow).execute(subscription_id=subscription_id)
    except uc.SubscriptionNotFound:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
