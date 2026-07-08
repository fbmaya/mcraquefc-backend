import uuid

from sqlalchemy.orm import Session

from app.contexts.school.domain.school_class import SchoolClass
from app.contexts.school.domain.enrollment import Enrollment
from app.contexts.school.domain.repositories import (
    ClassRepository, EnrollmentRepository, StudentLookup,
)
from app.models.class_ import Class as ClassORM, ClassEnrollment as EnrollmentORM
from app.models.student import Student as StudentORM


def _to_domain(row: ClassORM) -> SchoolClass:
    return SchoolClass(
        id=row.id, school_id=row.school_id, name=row.name, age_group=row.age_group,
        period=row.period, schedule=row.schedule, coach_id=row.coach_id, created_at=row.created_at,
    )


def _apply(row: ClassORM, c: SchoolClass) -> None:
    row.school_id = c.school_id
    row.name = c.name
    row.age_group = c.age_group
    row.period = c.period
    row.schedule = c.schedule
    row.coach_id = c.coach_id


class SqlAlchemyClassRepository(ClassRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def add(self, school_class: SchoolClass) -> None:
        row = self.session.get(ClassORM, school_class.id) or ClassORM(id=school_class.id)
        _apply(row, school_class)
        self.session.add(row)

    def get(self, class_id: str) -> SchoolClass | None:
        row = self.session.get(ClassORM, class_id)
        return _to_domain(row) if row else None

    def list_by_school(self, school_id: str) -> list[SchoolClass]:
        rows = self.session.query(ClassORM).filter(ClassORM.school_id == school_id).all()
        return [_to_domain(r) for r in rows]

    def remove(self, school_class: SchoolClass) -> None:
        row = self.session.get(ClassORM, school_class.id)
        if row:
            self.session.delete(row)

    def active_student_ids(self, class_id: str) -> list[str]:
        rows = (
            self.session.query(EnrollmentORM.student_id)
            .filter(EnrollmentORM.class_id == class_id, EnrollmentORM.active == True)  # noqa: E712
            .all()
        )
        return [r[0] for r in rows]


class SqlAlchemyEnrollmentRepository(EnrollmentRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def _row(self, class_id: str, student_id: str) -> EnrollmentORM | None:
        return (
            self.session.query(EnrollmentORM)
            .filter(EnrollmentORM.class_id == class_id, EnrollmentORM.student_id == student_id)
            .first()
        )

    def find(self, class_id: str, student_id: str) -> Enrollment | None:
        row = self._row(class_id, student_id)
        if row is None:
            return None
        return Enrollment(id=row.id, class_id=row.class_id, student_id=row.student_id, active=row.active)

    def create(self, id: str, class_id: str, student_id: str) -> None:
        self.session.add(EnrollmentORM(id=id, class_id=class_id, student_id=student_id, active=True))

    def set_active(self, class_id: str, student_id: str, active: bool) -> None:
        row = self._row(class_id, student_id)
        if row:
            row.active = active


class SqlAlchemyStudentLookup(StudentLookup):
    def __init__(self, session: Session):
        self.session = session

    def belongs_to_school(self, student_id: str, school_id: str) -> bool:
        row = self.session.get(StudentORM, student_id)
        return row is not None and row.school_id == school_id
