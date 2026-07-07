from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_parent
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.parent_link import ParentStudentLink
from app.models.payment import Payment
from app.models.evaluation import Evaluation
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.match import Match, MatchStat
from app.schemas.student import StudentOut
from app.schemas.payment import PaymentOut
from app.schemas.evaluation import EvaluationOut
from app.schemas.attendance import AttendanceSessionOut
from app.schemas.match import MatchOut
from app.services import stats
from app.services.parent_linking import reconcile_parent_links

router = APIRouter(prefix="/parent", tags=["parent"])


@router.get("/students", response_model=list[StudentOut])
def my_students(db: Session = Depends(get_db), current_user: User = Depends(require_parent)):
    # Reconcilia por email do responsável: pega filhos cadastrados após o login.
    reconcile_parent_links(db, current_user)
    links = db.query(ParentStudentLink).filter(ParentStudentLink.parent_id == current_user.id).all()
    student_ids = [l.student_id for l in links]
    return db.query(Student).filter(Student.id.in_(student_ids)).all()


def _assert_linked(parent_id: str, student_id: str, db: Session):
    link = (
        db.query(ParentStudentLink)
        .filter(ParentStudentLink.parent_id == parent_id, ParentStudentLink.student_id == student_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=403, detail="Acesso negado a este aluno")


@router.get("/students/{student_id}/summary")
def student_summary(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_parent)):
    _assert_linked(current_user.id, student_id, db)
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    performance = stats.student_performance(db, student)
    performance["peers"] = stats.peer_averages(db, student)
    return performance


@router.get("/students/{student_id}/payments", response_model=list[PaymentOut])
def student_payments(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_parent)):
    _assert_linked(current_user.id, student_id, db)
    return db.query(Payment).filter(Payment.student_id == student_id).order_by(Payment.month_key.desc()).all()


@router.get("/students/{student_id}/evaluations", response_model=list[EvaluationOut])
def student_evaluations(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_parent)):
    _assert_linked(current_user.id, student_id, db)
    return db.query(Evaluation).filter(Evaluation.student_id == student_id).order_by(Evaluation.date.desc()).all()


@router.get("/students/{student_id}/attendance", response_model=list[AttendanceSessionOut])
def student_attendance(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_parent)):
    _assert_linked(current_user.id, student_id, db)
    sessions = (
        db.query(AttendanceSession)
        .join(AttendanceRecord, AttendanceSession.id == AttendanceRecord.session_id)
        .filter(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceSession.date.desc())
        .all()
    )
    return sessions


@router.get("/students/{student_id}/matches", response_model=list[MatchOut])
def student_matches(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_parent)):
    _assert_linked(current_user.id, student_id, db)
    matches = (
        db.query(Match)
        .join(MatchStat, Match.id == MatchStat.match_id)
        .filter(MatchStat.student_id == student_id)
        .order_by(Match.date.desc())
        .all()
    )
    return matches
