import datetime as dt
from dataclasses import dataclass, field

from app.contexts.attendance.domain.session import AttendanceSession


@dataclass
class NewRecord:
    student_id: str
    present: bool = False
    justified: bool = False
    notes: str | None = None


@dataclass
class NewSession:
    class_id: str
    date: dt.date
    notes: str | None = None
    records: list[NewRecord] = field(default_factory=list)


@dataclass
class RecordView:
    id: str
    session_id: str
    student_id: str
    present: bool
    justified: bool
    notes: str | None


@dataclass
class SessionView:
    id: str
    class_id: str
    date: dt.date | None
    notes: str | None
    records: list[RecordView]
    created_at: dt.datetime | None

    @classmethod
    def of(cls, s: AttendanceSession) -> "SessionView":
        return cls(
            id=s.id, class_id=s.class_id, date=s.date, notes=s.notes, created_at=s.created_at,
            records=[
                RecordView(
                    id=r.id, session_id=s.id, student_id=r.student_id,
                    present=r.present, justified=r.justified, notes=r.notes,
                )
                for r in s.records
            ],
        )
