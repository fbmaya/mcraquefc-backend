import datetime as dt
from dataclasses import dataclass, field

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError


@dataclass(frozen=True)
class AttendanceRecordLine:
    id: str
    student_id: str
    present: bool = False
    justified: bool = False
    notes: str | None = None


@dataclass(eq=False)
class AttendanceSession(AggregateRoot):
    class_id: str = ""
    date: dt.date | None = None
    notes: str | None = None
    created_at: dt.datetime | None = None
    records: list[AttendanceRecordLine] = field(default_factory=list)

    @classmethod
    def register(cls, *, id: str, class_id: str, date: dt.date,
                 records: list[AttendanceRecordLine], notes: str | None = None) -> "AttendanceSession":
        if not class_id:
            raise ValidationError("Turma é obrigatória")
        return cls(id=id, class_id=class_id, date=date, notes=notes, records=list(records))
