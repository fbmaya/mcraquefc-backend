import uuid
import random
import string
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_manager, require_coach_or_manager
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate, StudentOut
from app.services import licensing

router = APIRouter(prefix="/students", tags=["students"])


def _school_id(user: User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=400, detail="Usuário não vinculado a uma escolinha")
    return user.school_id


def _generate_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# List/read: coach and manager can see students
@router.get("/", response_model=list[StudentOut])
def list_students(db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_manager)):
    return db.query(Student).filter(Student.school_id == _school_id(current_user)).all()


# Create/delete: manager only
@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(body: StudentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    licensing.assert_can_add_student(db, _school_id(current_user))
    code = _generate_code()
    while db.query(Student).filter(Student.access_code == code).first():
        code = _generate_code()
    student = Student(id=str(uuid.uuid4()), school_id=_school_id(current_user), access_code=code, **body.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_manager)):
    student = db.get(Student, student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return student


# Edit technical data: coach and manager
@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: str,
    body: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_manager),
):
    student = db.get(Student, student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


# Delete: manager only
@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    student = db.get(Student, student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    db.delete(student)
    db.commit()


# Regenerate access code: manager only
@router.post("/{student_id}/regenerate-code", response_model=StudentOut)
def regenerate_code(student_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    student = db.get(Student, student_id)
    if not student or student.school_id != _school_id(current_user):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    code = _generate_code()
    while db.query(Student).filter(Student.access_code == code).first():
        code = _generate_code()
    student.access_code = code
    db.commit()
    db.refresh(student)
    return student
