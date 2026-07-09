from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.deps import require_coach_or_manager
from app.models.user import User
from app.contexts.reporting.application import queries as q
from app.contexts.reporting.interface import deps

router = APIRouter(prefix="/stats", tags=["stats"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


@router.get("/overview")
def overview(reporting=Depends(deps.reporting_repo), current_user: User = Depends(require_coach_or_manager)):
    return q.SchoolOverview(reporting).execute(school_id=_school_id(current_user))


@router.get("/leaderboard")
def leaderboard(limit: int = Query(10, ge=1, le=50), reporting=Depends(deps.reporting_repo),
                current_user: User = Depends(require_coach_or_manager)):
    return q.Leaderboard(reporting).execute(school_id=_school_id(current_user), limit=limit)


@router.get("/students/{student_id}")
def student_stats(student_id: str, reporting=Depends(deps.reporting_repo),
                  current_user: User = Depends(require_coach_or_manager)):
    try:
        return q.StudentPerformance(reporting).execute(
            student_id=student_id, school_id=_school_id(current_user))
    except q.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")


@router.get("/students/{student_id}/peers")
def student_peers(student_id: str, reporting=Depends(deps.reporting_repo),
                  current_user: User = Depends(require_coach_or_manager)):
    try:
        return q.PeerAverages(reporting).execute(
            student_id=student_id, school_id=_school_id(current_user))
    except q.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
