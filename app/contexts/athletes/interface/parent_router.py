"""Portal do responsável (/parent/*).

O contexto Athletes é dono da relação responsável↔aluno, então hospeda o portal.
Cada endpoint valida o vínculo (via link_repo) e compõe leituras dos outros
contextos pelos respectivos casos de uso de leitura (sem escopo de escola —
o vínculo já autoriza)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_parent
from app.database import get_db
from app.models.user import User
from app.schemas.student import StudentOut
from app.schemas.payment import PaymentOut
from app.schemas.evaluation import EvaluationOut
from app.schemas.attendance import AttendanceSessionOut
from app.schemas.match import MatchOut

from app.contexts.athletes.application import use_cases as uc
from app.contexts.athletes.interface import deps

from app.contexts.billing.application import payment_use_cases as billing
from app.contexts.billing.interface import deps as billing_deps
from app.contexts.assessment.application import evaluation_use_cases as assessment
from app.contexts.assessment.interface import deps as assessment_deps
from app.contexts.attendance.application import attendance_use_cases as attendance
from app.contexts.attendance.interface import deps as attendance_deps
from app.contexts.performance.application import matches_use_cases as performance
from app.contexts.performance.interface import deps as performance_deps
from app.contexts.reporting.application import queries as reporting
from app.contexts.reporting.interface import deps as reporting_deps

router = APIRouter(prefix="/parent", tags=["parent"])


def _assert_linked(links, parent_id: str, student_id: str) -> None:
    if student_id not in links.student_ids_for_parent(parent_id):
        raise HTTPException(status_code=403, detail="Acesso negado a este aluno")


@router.get("/students", response_model=list[StudentOut])
def my_students(students=Depends(deps.student_repo), links=Depends(deps.link_repo), uow=Depends(deps.uow),
                current_user: User = Depends(require_parent)):
    return uc.ListChildrenForParent(students, links, uow).execute(
        parent_id=current_user.id, parent_email=current_user.email)


@router.get("/students/{student_id}/summary")
def student_summary(student_id: str, links=Depends(deps.link_repo),
                    reporting_repo=Depends(reporting_deps.reporting_repo),
                    current_user: User = Depends(require_parent)):
    _assert_linked(links, current_user.id, student_id)
    try:
        performance_view = reporting.StudentPerformance(reporting_repo).execute(student_id=student_id)
        performance_view["peers"] = reporting.PeerAverages(reporting_repo).execute(student_id=student_id)
    except reporting.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return performance_view


@router.get("/students/{student_id}/payments", response_model=list[PaymentOut])
def student_payments(student_id: str, links=Depends(deps.link_repo),
                     payments=Depends(billing_deps.payment_repo),
                     current_user: User = Depends(require_parent)):
    _assert_linked(links, current_user.id, student_id)
    return billing.ListPaymentsForStudent(payments).execute(student_id=student_id)


@router.get("/students/{student_id}/evaluations", response_model=list[EvaluationOut])
def student_evaluations(student_id: str, links=Depends(deps.link_repo),
                        evaluations=Depends(assessment_deps.evaluation_repo),
                        current_user: User = Depends(require_parent)):
    _assert_linked(links, current_user.id, student_id)
    return assessment.ListEvaluationsForStudent(evaluations).execute(student_id=student_id)


@router.get("/students/{student_id}/attendance", response_model=list[AttendanceSessionOut])
def student_attendance(student_id: str, links=Depends(deps.link_repo),
                       sessions=Depends(attendance_deps.attendance_repo),
                       current_user: User = Depends(require_parent)):
    _assert_linked(links, current_user.id, student_id)
    return attendance.ListSessionsForStudent(sessions).execute(student_id=student_id)


@router.get("/students/{student_id}/matches", response_model=list[MatchOut])
def student_matches(student_id: str, links=Depends(deps.link_repo),
                    matches=Depends(performance_deps.match_repo),
                    current_user: User = Depends(require_parent)):
    _assert_linked(links, current_user.id, student_id)
    return performance.ListMatchesForStudent(matches).execute(student_id=student_id)
