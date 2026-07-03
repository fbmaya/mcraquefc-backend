import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_manager, require_coach_or_manager
from app.database import get_db
from app.models.user import User
from app.models.class_ import Class, ClassEnrollment
from app.models.student import Student
from app.schemas.class_ import ClassCreate, ClassUpdate, ClassOut, EnrollmentCreate, EnrollmentOut

router = APIRouter(prefix="/classes", tags=["classes"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


# Read: coach and manager
@router.get("/", response_model=list[ClassOut])
def list_classes(db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_manager)):
    return db.query(Class).filter(Class.school_id == _school_id(current_user)).all()


# Create/edit/delete: manager only
@router.post("/", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(body: ClassCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    cls = Class(id=str(uuid.uuid4()), school_id=_school_id(current_user), **body.model_dump())
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


@router.patch("/{class_id}", response_model=ClassOut)
def update_class(
    class_id: str,
    body: ClassUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    cls = db.get(Class, class_id)
    if not cls or cls.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cls, field, value)
    db.commit()
    db.refresh(cls)
    return cls


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    cls = db.get(Class, class_id)
    if not cls or cls.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    db.delete(cls)
    db.commit()


# Enrollments: manager only
@router.post("/{class_id}/enroll", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll_student(
    class_id: str,
    body: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    cls = db.get(Class, class_id)
    if not cls or cls.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    # student must belong to the same school — never enroll another tenant's student
    student = db.get(Student, body.student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    existing = (
        db.query(ClassEnrollment)
        .filter(ClassEnrollment.class_id == class_id, ClassEnrollment.student_id == body.student_id)
        .first()
    )
    if existing:
        existing.active = True
        db.commit()
        db.refresh(existing)
        return existing
    enrollment = ClassEnrollment(id=str(uuid.uuid4()), class_id=class_id, student_id=body.student_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.delete("/{class_id}/enroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def unenroll_student(
    class_id: str,
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    enrollment = (
        db.query(ClassEnrollment)
        .filter(ClassEnrollment.class_id == class_id, ClassEnrollment.student_id == student_id)
        .first()
    )
    cls = db.get(Class, class_id)
    if not cls or cls.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if enrollment:
        enrollment.active = False
        db.commit()
