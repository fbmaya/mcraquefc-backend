from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import require_manager, require_coach_or_manager
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate, StudentOut
from app.contexts.platform.application import licensing
from app.database import get_db
from app.contexts.athletes.application.dtos import NewStudent
from app.contexts.athletes.application import use_cases as uc
from app.contexts.athletes.interface import deps

router = APIRouter(prefix="/students", tags=["students"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


@router.get("/", response_model=list[StudentOut])
def list_students(students=Depends(deps.student_repo), current_user: User = Depends(require_coach_or_manager)):
    return uc.ListStudents(students).execute(school_id=_school_id(current_user))


@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(body: StudentCreate, students=Depends(deps.student_repo), uow=Depends(deps.uow),
                   db=Depends(get_db), current_user: User = Depends(require_manager)):
    licensing.assert_can_add_student(db, _school_id(current_user))
    data = NewStudent(**body.model_dump())
    return uc.RegisterStudent(students, uow).execute(school_id=_school_id(current_user), data=data)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: str, students=Depends(deps.student_repo),
                current_user: User = Depends(require_coach_or_manager)):
    try:
        return uc.GetStudent(students).execute(school_id=_school_id(current_user), student_id=student_id)
    except uc.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: str, body: StudentUpdate, students=Depends(deps.student_repo), uow=Depends(deps.uow),
                   current_user: User = Depends(require_coach_or_manager)):
    try:
        return uc.UpdateStudent(students, uow).execute(
            school_id=_school_id(current_user), student_id=student_id, changes=body.model_dump(exclude_unset=True))
    except uc.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: str, students=Depends(deps.student_repo), uow=Depends(deps.uow),
                   current_user: User = Depends(require_manager)):
    try:
        uc.DeleteStudent(students, uow).execute(school_id=_school_id(current_user), student_id=student_id)
    except uc.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
