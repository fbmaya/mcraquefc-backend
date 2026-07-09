from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import require_coach_or_manager
from app.models.user import User
from app.schemas.evaluation import EvaluationCreate, EvaluationOut
from app.contexts.assessment.application.evaluation_dtos import NewEvaluation
from app.contexts.assessment.application import evaluation_use_cases as uc
from app.contexts.assessment.domain.evaluation import SKILLS
from app.contexts.assessment.interface import deps

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


def _to_new_evaluation(body: EvaluationCreate) -> NewEvaluation:
    data = body.model_dump()
    skills = {k: data.pop(k) for k in SKILLS}
    return NewEvaluation(student_id=data["student_id"], date=data["date"],
                         skills=skills, notes=data.get("notes"))


@router.get("/", response_model=list[EvaluationOut])
def list_evaluations(student_id: str | None = None, evaluations=Depends(deps.evaluation_repo),
                     current_user: User = Depends(require_coach_or_manager)):
    return uc.ListEvaluations(evaluations).execute(
        school_id=_school_id(current_user), student_id=student_id)


@router.post("/", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
def create_evaluation(body: EvaluationCreate, evaluations=Depends(deps.evaluation_repo),
                      uow=Depends(deps.uow), current_user: User = Depends(require_coach_or_manager)):
    try:
        return uc.CreateEvaluation(evaluations, uow).execute(
            school_id=_school_id(current_user), evaluated_by=current_user.id,
            data=_to_new_evaluation(body))
    except uc.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation(evaluation_id: str, evaluations=Depends(deps.evaluation_repo),
                      uow=Depends(deps.uow), current_user: User = Depends(require_coach_or_manager)):
    try:
        uc.DeleteEvaluation(evaluations, uow).execute(
            school_id=_school_id(current_user), evaluation_id=evaluation_id)
    except uc.EvaluationNotFound:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
