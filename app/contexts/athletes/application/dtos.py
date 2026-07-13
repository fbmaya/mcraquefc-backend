import datetime as dt
from dataclasses import dataclass

from app.contexts.athletes.domain.student import Student


@dataclass
class NewStudent:
    name: str
    guardian_email: str
    birth_date: dt.date | None = None
    position: str | None = None
    foot: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    notes: str | None = None


@dataclass
class StudentView:
    id: str
    school_id: str
    name: str
    birth_date: dt.date | None
    photo_url: str | None
    position: str | None
    foot: str | None
    guardian_name: str | None
    guardian_email: str | None
    guardian_phone: str | None
    notes: str | None
    active: bool
    created_at: dt.datetime | None
    # Preenchido só no portal do responsável (filhos podem estar em escolas diferentes).
    school_name: str | None = None

    @classmethod
    def of(cls, s: Student) -> "StudentView":
        return cls(
            id=s.id, school_id=s.school_id, name=s.name, birth_date=s.birth_date,
            photo_url=s.photo_url, position=s.position, foot=s.foot,
            guardian_name=s.guardian_name,
            guardian_email=s.guardian_email.value if s.guardian_email else None,
            guardian_phone=s.guardian_phone, notes=s.notes, active=s.active,
            created_at=s.created_at,
        )
