import uuid

from sqlalchemy.orm import Session

from app.contexts.attendance.domain.session import AttendanceSession, AttendanceRecordLine
from app.contexts.attendance.domain.repositories import AttendanceRepository
from app.models.attendance import AttendanceSession as SessionORM, AttendanceRecord as RecordORM
from app.models.class_ import Class as ClassORM
from app.models.student import Student as StudentORM


def _to_domain(row: SessionORM) -> AttendanceSession:
    return AttendanceSession(
        id=row.id, class_id=row.class_id, date=row.date, notes=row.notes, created_at=row.created_at,
        records=[
            AttendanceRecordLine(
                id=r.id, student_id=r.student_id, present=r.present,
                justified=r.justified, notes=r.notes,
            )
            for r in row.records
        ],
    )


class SqlAlchemyAttendanceRepository(AttendanceRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def next_record_id(self) -> str:
        return str(uuid.uuid4())

    def add(self, session: AttendanceSession) -> None:
        self.session.add(SessionORM(
            id=session.id, class_id=session.class_id, date=session.date, notes=session.notes,
        ))
        for r in session.records:
            self.session.add(RecordORM(
                id=r.id, session_id=session.id, student_id=r.student_id,
                present=r.present, justified=r.justified, notes=r.notes,
            ))

    def get(self, session_id: str) -> AttendanceSession | None:
        row = self.session.get(SessionORM, session_id)
        return _to_domain(row) if row else None

    def list_by_school(self, school_id: str, class_id: str | None = None) -> list[AttendanceSession]:
        q = (
            self.session.query(SessionORM)
            .join(ClassORM, SessionORM.class_id == ClassORM.id)
            .filter(ClassORM.school_id == school_id)
        )
        if class_id:
            q = q.filter(SessionORM.class_id == class_id)
        return [_to_domain(r) for r in q.order_by(SessionORM.date.desc()).all()]

    def remove(self, session: AttendanceSession) -> None:
        # delete children first — the ORM has no cascade and session_id is NOT NULL
        self.session.query(RecordORM).filter(RecordORM.session_id == session.id).delete()
        row = self.session.get(SessionORM, session.id)
        if row:
            self.session.delete(row)

    def class_belongs_to_school(self, class_id: str, school_id: str) -> bool:
        row = self.session.get(ClassORM, class_id)
        return row is not None and row.school_id == school_id

    def students_all_in_school(self, student_ids: set[str], school_id: str) -> bool:
        ids = set(student_ids)
        if not ids:
            return True
        valid = (
            self.session.query(StudentORM.id)
            .filter(StudentORM.id.in_(ids), StudentORM.school_id == school_id)
            .count()
        )
        return valid == len(ids)
