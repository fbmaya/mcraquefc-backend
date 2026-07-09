from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import require_manager
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentOut
from app.contexts.billing.application.payment_dtos import NewPayment
from app.contexts.billing.application import payment_use_cases as uc
from app.contexts.billing.interface import deps

router = APIRouter(prefix="/payments", tags=["payments"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


@router.get("/", response_model=list[PaymentOut])
def list_payments(month_key: str | None = None, student_id: str | None = None,
                  payments=Depends(deps.payment_repo), current_user: User = Depends(require_manager)):
    return uc.ListPayments(payments).execute(
        school_id=_school_id(current_user), month_key=month_key, student_id=student_id)


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentCreate, payments=Depends(deps.payment_repo), uow=Depends(deps.uow),
                   current_user: User = Depends(require_manager)):
    try:
        return uc.CreatePayment(payments, uow).execute(
            school_id=_school_id(current_user), data=NewPayment(**body.model_dump()))
    except uc.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    except uc.DuplicatePayment:
        raise HTTPException(status_code=409, detail="Pagamento já existe para esse mês")


@router.patch("/{payment_id}", response_model=PaymentOut)
def update_payment(payment_id: str, body: PaymentUpdate, payments=Depends(deps.payment_repo),
                   uow=Depends(deps.uow), current_user: User = Depends(require_manager)):
    try:
        return uc.UpdatePayment(payments, uow).execute(
            school_id=_school_id(current_user), payment_id=payment_id,
            changes=body.model_dump(exclude_unset=True))
    except uc.PaymentNotFound:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: str, payments=Depends(deps.payment_repo), uow=Depends(deps.uow),
                   current_user: User = Depends(require_manager)):
    try:
        uc.DeletePayment(payments, uow).execute(school_id=_school_id(current_user), payment_id=payment_id)
    except uc.PaymentNotFound:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
