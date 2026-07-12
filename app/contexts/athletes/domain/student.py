import datetime as dt
from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError
from app.shared.domain.value_objects import Email

_OPTIONAL = ("birth_date", "position", "foot", "guardian_name", "guardian_phone", "notes", "photo_url")


@dataclass(eq=False)
class Student(AggregateRoot):
    school_id: str = ""
    name: str = ""
    guardian_email: Email | None = None
    birth_date: dt.date | None = None
    position: str | None = None
    foot: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    notes: str | None = None
    photo_url: str | None = None
    active: bool = True
    created_at: dt.datetime | None = None

    @classmethod
    def register(cls, *, id: str, school_id: str, name: str,
                 guardian_email: Email | None, **optional) -> "Student":
        if guardian_email is None:
            raise ValidationError("E-mail do responsável é obrigatório")
        if not name or not name.strip():
            raise ValidationError("Nome do aluno é obrigatório")
        data = {k: optional.get(k) for k in _OPTIONAL}
        return cls(id=id, school_id=school_id, name=name.strip(),
                   guardian_email=guardian_email, **data)

    def change(self, **fields) -> None:
        for key, value in fields.items():
            if key in ("name", "guardian_email", *_OPTIONAL):
                setattr(self, key, value)

    def set_active(self, value: bool) -> None:
        self.active = value


def matches_guardian(student: Student, email: Email) -> bool:
    return student.guardian_email is not None and student.guardian_email == email
