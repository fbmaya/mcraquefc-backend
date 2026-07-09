import datetime as dt
from dataclasses import dataclass, field

from app.contexts.performance.domain.match import Match


@dataclass
class NewMatchStat:
    student_id: str
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    rating: float | None = None
    played: bool = True
    notes: str | None = None


@dataclass
class NewMatch:
    date: dt.date
    opponent: str
    location: str | None = None
    home: bool = True
    score_us: int | None = None
    score_them: int | None = None
    category: str | None = None
    notes: str | None = None
    stats: list[NewMatchStat] = field(default_factory=list)


@dataclass
class MatchStatView:
    id: str
    student_id: str
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    rating: float | None
    played: bool
    notes: str | None


@dataclass
class MatchView:
    id: str
    school_id: str
    date: dt.date | None
    opponent: str
    location: str | None
    home: bool
    score_us: int | None
    score_them: int | None
    category: str | None
    notes: str | None
    stats: list[MatchStatView]
    created_at: dt.datetime | None

    @classmethod
    def of(cls, m: Match) -> "MatchView":
        return cls(
            id=m.id, school_id=m.school_id, date=m.date, opponent=m.opponent,
            location=m.location, home=m.home, score_us=m.score_us, score_them=m.score_them,
            category=m.category, notes=m.notes, created_at=m.created_at,
            stats=[
                MatchStatView(
                    id=s.id, student_id=s.student_id, goals=s.goals, assists=s.assists,
                    yellow_cards=s.yellow_cards, red_cards=s.red_cards, rating=s.rating,
                    played=s.played, notes=s.notes,
                )
                for s in m.stats
            ],
        )
