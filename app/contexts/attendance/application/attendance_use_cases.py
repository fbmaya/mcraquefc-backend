from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.contexts.attendance.domain.session import AttendanceSession, AttendanceRecordLine
from app.contexts.attendance.domain.repositories import AttendanceRepository
from app.contexts.attendance.application.attendance_dtos import NewSession, SessionView


class ClassNotFound(DomainError):
    pass


class InvalidRecords(DomainError):
    pass


class SessionNotFound(DomainError):
    pass


class CreateSession:
    def __init__(self, sessions: AttendanceRepository, uow: UnitOfWork):
        self.sessions, self.uow = sessions, uow

    def execute(self, *, school_id: str, data: NewSession) -> SessionView:
        if not self.sessions.class_belongs_to_school(data.class_id, school_id):
            raise ClassNotFound("Turma não encontrada")
        student_ids = {r.student_id for r in data.records}
        if not self.sessions.students_all_in_school(student_ids, school_id):
            raise InvalidRecords("Registro contém alunos de outra escola ou inexistentes")
        lines = [
            AttendanceRecordLine(
                id=self.sessions.next_record_id(), student_id=r.student_id,
                present=r.present, justified=r.justified, notes=r.notes,
            )
            for r in data.records
        ]
        session = AttendanceSession.register(
            id=self.sessions.next_id(), class_id=data.class_id, date=data.date,
            notes=data.notes, records=lines,
        )
        self.sessions.add(session)
        self.uow.commit()
        saved = self.sessions.get(session.id)  # relê p/ created_at
        return SessionView.of(saved)


class ListSessions:
    def __init__(self, sessions: AttendanceRepository):
        self.sessions = sessions

    def execute(self, *, school_id: str, class_id: str | None = None) -> list[SessionView]:
        return [SessionView.of(s) for s in self.sessions.list_by_school(school_id, class_id)]


class ListSessionsForStudent:
    """Portal do responsável: presenças de um aluno (sem escopo de escola)."""

    def __init__(self, sessions: AttendanceRepository):
        self.sessions = sessions

    def execute(self, *, student_id: str) -> list[SessionView]:
        return [SessionView.of(s) for s in self.sessions.list_by_student(student_id)]


class DeleteSession:
    def __init__(self, sessions: AttendanceRepository, uow: UnitOfWork):
        self.sessions, self.uow = sessions, uow

    def execute(self, *, school_id: str, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session is None or not self.sessions.class_belongs_to_school(session.class_id, school_id):
            raise SessionNotFound("Sessão não encontrada")
        self.sessions.remove(session)
        self.uow.commit()
