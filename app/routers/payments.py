import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_manager
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentOut

router = APIRouter(prefix="/payments", tags=["payments"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


# All payment endpoints: manager only (financial is manager-exclusive)
@router.get("/", response_model=list[PaymentOut])
def list_payments(
    month_key: str | None = None,
    student_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    q = (
        db.query(Payment)
        .join(Student, Payment.student_id == Student.id)
        .filter(Student.school_id == _school_id(current_user))
    )
    if month_key:
        q = q.filter(Payment.month_key == month_key)
    if student_id:
        q = q.filter(Payment.student_id == student_id)
    return q.all()


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    student = db.get(Student, body.student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    existing = (
        db.query(Payment)
        .filter(Payment.student_id == body.student_id, Payment.month_key == body.month_key)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Pagamento já existe para esse mês")
    payment = Payment(id=str(uuid.uuid4()), **body.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentOut)
def update_payment(
    payment_id: str,
    body: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    student = db.get(Student, payment.student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=403, detail="Acesso negado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(payment, field, value)
    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    student = db.get(Student, payment.student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=403, detail="Acesso negado")
    db.delete(payment)
    db.commit()
