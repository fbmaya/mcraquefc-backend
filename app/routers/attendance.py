import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_coach_or_manager
from app.database import get_db
from app.models.user import User
from app.models.class_ import Class
from app.models.student import Student
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.schemas.attendance import AttendanceSessionCreate, AttendanceSessionOut

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


# Coach and manager manage attendance (coach takes roll call)
@router.get("/", response_model=list[AttendanceSessionOut])
def list_sessions(
    class_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    q = (
        db.query(AttendanceSession)
        .join(Class, AttendanceSession.class_id == Class.id)
        .filter(Class.school_id == _school_id(current_user))
    )
    if class_id:
        q = q.filter(AttendanceSession.class_id == class_id)
    return q.order_by(AttendanceSession.date.desc()).all()


@router.post("/", response_model=AttendanceSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: AttendanceSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    cls = db.get(Class, body.class_id)
    if not cls or cls.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Turma não encontrada")

    # every record must reference a student of the same school
    student_ids = {rec.student_id for rec in body.records}
    if student_ids:
        valid = (
            db.query(Student.id)
            .filter(Student.id.in_(student_ids), Student.school_id == _school_id(current_user))
            .count()
        )
        if valid != len(student_ids):
            raise HTTPException(status_code=400, detail="Registro contém alunos de outra escola ou inexistentes")

    session_id = str(uuid.uuid4())
    session = AttendanceSession(
        id=session_id,
        class_id=body.class_id,
        date=body.date,
        notes=body.notes,
    )
    db.add(session)
    for rec in body.records:
        db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=session_id, **rec.model_dump()))
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    session = db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    cls = db.get(Class, session.class_id)
    if not cls or cls.school_id != _school_id(current_user):
        raise HTTPException(status_code=403, detail="Acesso negado")
    db.delete(session)
    db.commit()
