import datetime as dt
from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError

_OPTIONAL = ("age_group", "period", "schedule", "coach_id")


@dataclass(eq=False)
class SchoolClass(AggregateRoot):
    school_id: str = ""
    name: str = ""
    age_group: str | None = None
    period: str | None = None
    schedule: str | None = None
    coach_id: str | None = None
    created_at: dt.datetime | None = None

    @classmethod
    def register(cls, *, id: str, school_id: str, name: str, **optional) -> "SchoolClass":
        if not name or not name.strip():
            raise ValidationError("Nome da turma é obrigatório")
        data = {k: optional.get(k) for k in _OPTIONAL}
        return cls(id=id, school_id=school_id, name=name.strip(), **data)

    def change(self, **fields) -> None:
        for key, value in fields.items():
            if key in ("name", *_OPTIONAL):
                setattr(self, key, value)
