import datetime as dt
from dataclasses import dataclass, field

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError

_SCALARS = ("opponent", "location", "home", "score_us", "score_them", "category", "notes")


@dataclass(frozen=True)
class MatchStatLine:
    id: str
    student_id: str
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    rating: float | None = None
    played: bool = True
    notes: str | None = None


@dataclass(eq=False)
class Match(AggregateRoot):
    school_id: str = ""
    date: dt.date | None = None
    opponent: str = ""
    location: str | None = None
    home: bool = True
    score_us: int | None = None
    score_them: int | None = None
    category: str | None = None
    notes: str | None = None
    created_at: dt.datetime | None = None
    stats: list[MatchStatLine] = field(default_factory=list)

    @classmethod
    def register(cls, *, id: str, school_id: str, date: dt.date, opponent: str,
                 stats: list[MatchStatLine], home: bool = True, location: str | None = None,
                 score_us: int | None = None, score_them: int | None = None,
                 category: str | None = None, notes: str | None = None) -> "Match":
        if not opponent or not opponent.strip():
            raise ValidationError("Adversário é obrigatório")
        return cls(
            id=id, school_id=school_id, date=date, opponent=opponent.strip(),
            home=home, location=location, score_us=score_us, score_them=score_them,
            category=category, notes=notes, stats=list(stats),
        )

    def change_fields(self, **fields) -> None:
        for key, value in fields.items():
            if key in _SCALARS:
                setattr(self, key, value)
