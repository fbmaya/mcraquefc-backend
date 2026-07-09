from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import require_coach_or_manager
from app.models.user import User
from app.schemas.attendance import AttendanceSessionCreate, AttendanceSessionOut
from app.contexts.attendance.application.attendance_dtos import NewSession, NewRecord
from app.contexts.attendance.application import attendance_use_cases as uc
from app.contexts.attendance.interface import deps

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


def _to_new_session(body: AttendanceSessionCreate) -> NewSession:
    data = body.model_dump()
    records = [NewRecord(**r) for r in data.pop("records")]
    return NewSession(records=records, **data)


@router.get("/", response_model=list[AttendanceSessionOut])
def list_sessions(class_id: str | None = None, sessions=Depends(deps.attendance_repo),
                  current_user: User = Depends(require_coach_or_manager)):
    return uc.ListSessions(sessions).execute(school_id=_school_id(current_user), class_id=class_id)


@router.post("/", response_model=AttendanceSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(body: AttendanceSessionCreate, sessions=Depends(deps.attendance_repo),
                   uow=Depends(deps.uow), current_user: User = Depends(require_coach_or_manager)):
    try:
        return uc.CreateSession(sessions, uow).execute(
            school_id=_school_id(current_user), data=_to_new_session(body))
    except uc.ClassNotFound:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    except uc.InvalidRecords:
        raise HTTPException(status_code=400, detail="Registro contém alunos de outra escola ou inexistentes")


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, sessions=Depends(deps.attendance_repo), uow=Depends(deps.uow),
                   current_user: User = Depends(require_coach_or_manager)):
    try:
        uc.DeleteSession(sessions, uow).execute(school_id=_school_id(current_user), session_id=session_id)
    except uc.SessionNotFound:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
