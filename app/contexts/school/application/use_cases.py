from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.contexts.school.domain.school_class import SchoolClass
from app.contexts.school.domain.repositories import (
    ClassRepository, EnrollmentRepository, StudentLookup,
)
from app.contexts.school.application.dtos import NewClass, ClassView, EnrollmentView

_UPDATABLE = ("name", "age_group", "period", "schedule", "coach_id")


class ClassNotFound(DomainError):
    pass


class StudentNotFound(DomainError):
    pass


def _require(classes: ClassRepository, school_id: str, class_id: str) -> SchoolClass:
    c = classes.get(class_id)
    if c is None or c.school_id != school_id:
        raise ClassNotFound("Turma não encontrada")
    return c


class CreateClass:
    def __init__(self, classes: ClassRepository, uow: UnitOfWork):
        self.classes, self.uow = classes, uow

    def execute(self, *, school_id: str, data: NewClass) -> ClassView:
        c = SchoolClass.register(
            id=self.classes.next_id(), school_id=school_id, name=data.name,
            age_group=data.age_group, period=data.period,
            schedule=data.schedule, coach_id=data.coach_id,
        )
        self.classes.add(c)
        self.uow.commit()
        saved = self.classes.get(c.id)  # relê p/ created_at
        return ClassView.of(saved, self.classes.active_student_ids(saved.id))


class UpdateClass:
    def __init__(self, classes: ClassRepository, uow: UnitOfWork):
        self.classes, self.uow = classes, uow

    def execute(self, *, school_id: str, class_id: str, changes: dict) -> ClassView:
        c = _require(self.classes, school_id, class_id)
        fields = {k: v for k, v in changes.items() if k in _UPDATABLE and v is not None}
        c.change(**fields)
        self.classes.add(c)  # persiste (lição da Fase 1)
        self.uow.commit()
        return ClassView.of(c, self.classes.active_student_ids(c.id))


class ListClasses:
    def __init__(self, classes: ClassRepository):
        self.classes = classes

    def execute(self, *, school_id: str) -> list[ClassView]:
        return [
            ClassView.of(c, self.classes.active_student_ids(c.id))
            for c in self.classes.list_by_school(school_id)
        ]


class DeleteClass:
    def __init__(self, classes: ClassRepository, uow: UnitOfWork):
        self.classes, self.uow = classes, uow

    def execute(self, *, school_id: str, class_id: str) -> None:
        self.classes.remove(_require(self.classes, school_id, class_id))
        self.uow.commit()


class EnrollStudent:
    def __init__(self, classes: ClassRepository, enrollments: EnrollmentRepository,
                 students: StudentLookup, uow: UnitOfWork):
        self.classes, self.enrollments, self.students, self.uow = classes, enrollments, students, uow

    def execute(self, *, school_id: str, class_id: str, student_id: str) -> EnrollmentView:
        _require(self.classes, school_id, class_id)
        if not self.students.belongs_to_school(student_id, school_id):
            raise StudentNotFound("Aluno não encontrado")
        existing = self.enrollments.find(class_id, student_id)
        if existing is not None:
            if not existing.active:
                self.enrollments.set_active(class_id, student_id, True)
            enrollment_id = existing.id
        else:
            enrollment_id = self.enrollments.next_id()
            self.enrollments.create(enrollment_id, class_id, student_id)
        self.uow.commit()
        return EnrollmentView(id=enrollment_id, class_id=class_id, student_id=student_id, active=True)


class UnenrollStudent:
    def __init__(self, classes: ClassRepository, enrollments: EnrollmentRepository, uow: UnitOfWork):
        self.classes, self.enrollments, self.uow = classes, enrollments, uow

    def execute(self, *, school_id: str, class_id: str, student_id: str) -> None:
        _require(self.classes, school_id, class_id)
        if self.enrollments.find(class_id, student_id) is not None:
            self.enrollments.set_active(class_id, student_id, False)
            self.uow.commit()
