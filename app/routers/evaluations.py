import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_coach_or_manager
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.evaluation import Evaluation
from app.schemas.evaluation import EvaluationCreate, EvaluationOut

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


# Coach and manager can create/read/delete evaluations
@router.get("/", response_model=list[EvaluationOut])
def list_evaluations(
    student_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    q = (
        db.query(Evaluation)
        .join(Student, Evaluation.student_id == Student.id)
        .filter(Student.school_id == _school_id(current_user))
    )
    if student_id:
        q = q.filter(Evaluation.student_id == student_id)
    return q.order_by(Evaluation.date.desc()).all()


@router.post("/", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
def create_evaluation(
    body: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    student = db.get(Student, body.student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    evaluation = Evaluation(id=str(uuid.uuid4()), evaluated_by=current_user.id, **body.model_dump())
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    ev = db.get(Evaluation, evaluation_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    student = db.get(Student, ev.student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=403, detail="Acesso negado")
    db.delete(ev)
    db.commit()
