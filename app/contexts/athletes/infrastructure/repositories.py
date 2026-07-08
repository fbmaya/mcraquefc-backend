import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.shared.domain.value_objects import Email
from app.contexts.athletes.domain.student import Student
from app.contexts.athletes.domain.repositories import StudentRepository, ParentLinkRepository
from app.models.student import Student as StudentORM
from app.models.parent_link import ParentStudentLink as LinkORM


def _to_domain(row: StudentORM) -> Student:
    return Student(
        id=row.id, school_id=row.school_id, name=row.name,
        guardian_email=Email.try_parse(row.guardian_email),
        birth_date=row.birth_date, position=row.position, foot=row.foot,
        guardian_name=row.guardian_name, guardian_phone=row.guardian_phone,
        notes=row.notes, photo_url=row.photo_url, created_at=row.created_at,
    )


def _apply(row: StudentORM, s: Student) -> None:
    row.school_id = s.school_id
    row.name = s.name
    row.guardian_email = s.guardian_email.value if s.guardian_email else None
    row.birth_date = s.birth_date
    row.position = s.position
    row.foot = s.foot
    row.guardian_name = s.guardian_name
    row.guardian_phone = s.guardian_phone
    row.notes = s.notes
    row.photo_url = s.photo_url


class SqlAlchemyStudentRepository(StudentRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def add(self, student: Student) -> None:
        row = self.session.get(StudentORM, student.id) or StudentORM(id=student.id)
        _apply(row, student)
        self.session.add(row)

    def get(self, student_id: str) -> Student | None:
        row = self.session.get(StudentORM, student_id)
        return _to_domain(row) if row else None

    def list_by_school(self, school_id: str) -> list[Student]:
        rows = self.session.query(StudentORM).filter(StudentORM.school_id == school_id).all()
        return [_to_domain(r) for r in rows]

    def list_by_guardian_email(self, email: Email) -> list[Student]:
        rows = (
            self.session.query(StudentORM)
            .filter(func.lower(StudentORM.guardian_email) == email.value)
            .all()
        )
        return [_to_domain(r) for r in rows]

    def remove(self, student: Student) -> None:
        row = self.session.get(StudentORM, student.id)
        if row:
            self.session.delete(row)


class SqlAlchemyParentLinkRepository(ParentLinkRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def student_ids_for_parent(self, parent_id: str) -> set[str]:
        rows = self.session.query(LinkORM.student_id).filter(LinkORM.parent_id == parent_id).all()
        return {r[0] for r in rows}

    def link(self, parent_id: str, student_id: str) -> None:
        self.session.add(LinkORM(id=self.next_id(), parent_id=parent_id, student_id=student_id))
