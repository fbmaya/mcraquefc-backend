from app.shared.domain.errors import DomainError
from app.shared.domain.value_objects import Email
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.contexts.athletes.domain.student import Student
from app.contexts.athletes.domain.repositories import StudentRepository, ParentLinkRepository
from app.contexts.athletes.application.dtos import NewStudent, StudentView

_UPDATABLE = ("name", "birth_date", "position", "foot", "guardian_name", "guardian_phone", "notes", "photo_url")


class StudentNotFound(DomainError):
    pass


def _require(students: StudentRepository, school_id: str, student_id: str) -> Student:
    s = students.get(student_id)
    if s is None or s.school_id != school_id:
        raise StudentNotFound("Aluno não encontrado")
    return s


class RegisterStudent:
    def __init__(self, students: StudentRepository, uow: UnitOfWork):
        self.students, self.uow = students, uow

    def execute(self, *, school_id: str, data: NewStudent) -> StudentView:
        student = Student.register(
            id=self.students.next_id(), school_id=school_id, name=data.name,
            guardian_email=Email.parse(data.guardian_email),
            birth_date=data.birth_date, position=data.position, foot=data.foot,
            guardian_name=data.guardian_name, guardian_phone=data.guardian_phone, notes=data.notes,
        )
        self.students.add(student)
        self.uow.commit()
        # relê para popular created_at (server_default) na resposta
        return StudentView.of(self.students.get(student.id))


class UpdateStudent:
    def __init__(self, students: StudentRepository, uow: UnitOfWork):
        self.students, self.uow = students, uow

    def execute(self, *, school_id: str, student_id: str, changes: dict) -> StudentView:
        student = _require(self.students, school_id, student_id)
        fields = {k: v for k, v in changes.items() if k in _UPDATABLE and v is not None}
        if "guardian_email" in changes and changes["guardian_email"] is not None:
            fields["guardian_email"] = Email.parse(changes["guardian_email"])
        student.change(**fields)
        self.students.add(student)
        self.uow.commit()
        return StudentView.of(student)


class SetStudentActive:
    def __init__(self, students: StudentRepository, uow: UnitOfWork):
        self.students, self.uow = students, uow

    def execute(self, *, school_id: str, student_id: str, active: bool) -> StudentView:
        student = _require(self.students, school_id, student_id)
        student.set_active(active)
        self.students.add(student)
        self.uow.commit()
        return StudentView.of(student)


class GetStudent:
    def __init__(self, students: StudentRepository):
        self.students = students

    def execute(self, *, school_id: str, student_id: str) -> StudentView:
        return StudentView.of(_require(self.students, school_id, student_id))


class ListStudents:
    def __init__(self, students: StudentRepository):
        self.students = students

    def execute(self, *, school_id: str) -> list[StudentView]:
        return [StudentView.of(s) for s in self.students.list_by_school(school_id)]


class DeleteStudent:
    def __init__(self, students: StudentRepository, uow: UnitOfWork):
        self.students, self.uow = students, uow

    def execute(self, *, school_id: str, student_id: str) -> None:
        self.students.remove(_require(self.students, school_id, student_id))
        self.uow.commit()


class ListChildrenForParent:
    def __init__(self, students: StudentRepository, links: ParentLinkRepository, uow: UnitOfWork):
        self.students, self.links, self.uow = students, links, uow

    def execute(self, *, parent_id: str, parent_email: str) -> list[StudentView]:
        email = Email.try_parse(parent_email)
        if email is not None:
            matched = self.students.list_by_guardian_email(email)
            existing = self.links.student_ids_for_parent(parent_id)
            created = False
            for s in matched:
                if s.id not in existing:
                    self.links.link(parent_id, s.id)
                    created = True
            if created:
                self.uow.commit()
        ids = self.links.student_ids_for_parent(parent_id)
        return [StudentView.of(s) for sid in ids if (s := self.students.get(sid))]
