from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_coach_or_manager
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.services import stats

router = APIRouter(prefix="/stats", tags=["stats"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


def _get_student_in_school(db: Session, student_id: str, school_id: str) -> Student:
    student = db.get(Student, student_id)
    if not student or student.school_id != school_id:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return student


@router.get("/overview")
def overview(db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_manager)):
    school_id = _school_id(current_user)
    data = stats.school_overview(db, school_id)
    data["top_scorers"] = stats.top_scorers(db, school_id)
    return data


@router.get("/leaderboard")
def leaderboard(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    return {"top_scorers": stats.top_scorers(db, _school_id(current_user), limit=limit)}


@router.get("/students/{student_id}")
def student_stats(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    student = _get_student_in_school(db, student_id, _school_id(current_user))
    return stats.student_performance(db, student)


@router.get("/students/{student_id}/peers")
def student_peers(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    student = _get_student_in_school(db, student_id, _school_id(current_user))
    return stats.peer_averages(db, student)
