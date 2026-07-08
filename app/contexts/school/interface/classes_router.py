from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import require_manager, require_coach_or_manager
from app.models.user import User
from app.schemas.class_ import ClassCreate, ClassUpdate, ClassOut, EnrollmentCreate, EnrollmentOut
from app.contexts.school.application.dtos import NewClass
from app.contexts.school.application import use_cases as uc
from app.contexts.school.interface import deps

router = APIRouter(prefix="/classes", tags=["classes"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


@router.get("/", response_model=list[ClassOut])
def list_classes(classes=Depends(deps.class_repo), current_user: User = Depends(require_coach_or_manager)):
    return uc.ListClasses(classes).execute(school_id=_school_id(current_user))


@router.post("/", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(body: ClassCreate, classes=Depends(deps.class_repo), uow=Depends(deps.uow),
                 current_user: User = Depends(require_manager)):
    return uc.CreateClass(classes, uow).execute(school_id=_school_id(current_user), data=NewClass(**body.model_dump()))


@router.patch("/{class_id}", response_model=ClassOut)
def update_class(class_id: str, body: ClassUpdate, classes=Depends(deps.class_repo), uow=Depends(deps.uow),
                 current_user: User = Depends(require_manager)):
    try:
        return uc.UpdateClass(classes, uow).execute(
            school_id=_school_id(current_user), class_id=class_id, changes=body.model_dump(exclude_unset=True))
    except uc.ClassNotFound:
        raise HTTPException(status_code=404, detail="Turma não encontrada")


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: str, classes=Depends(deps.class_repo), uow=Depends(deps.uow),
                 current_user: User = Depends(require_manager)):
    try:
        uc.DeleteClass(classes, uow).execute(school_id=_school_id(current_user), class_id=class_id)
    except uc.ClassNotFound:
        raise HTTPException(status_code=404, detail="Turma não encontrada")


@router.post("/{class_id}/enroll", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll_student(class_id: str, body: EnrollmentCreate, classes=Depends(deps.class_repo),
                   enrollments=Depends(deps.enrollment_repo), students=Depends(deps.student_lookup),
                   uow=Depends(deps.uow), current_user: User = Depends(require_manager)):
    try:
        return uc.EnrollStudent(classes, enrollments, students, uow).execute(
            school_id=_school_id(current_user), class_id=class_id, student_id=body.student_id)
    except uc.ClassNotFound:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    except uc.StudentNotFound:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")


@router.delete("/{class_id}/enroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def unenroll_student(class_id: str, student_id: str, classes=Depends(deps.class_repo),
                     enrollments=Depends(deps.enrollment_repo), uow=Depends(deps.uow),
                     current_user: User = Depends(require_manager)):
    try:
        uc.UnenrollStudent(classes, enrollments, uow).execute(
            school_id=_school_id(current_user), class_id=class_id, student_id=student_id)
    except uc.ClassNotFound:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
