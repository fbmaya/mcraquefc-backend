import uuid

from sqlalchemy.orm import Session

from app.contexts.performance.domain.match import Match, MatchStatLine
from app.contexts.performance.domain.repositories import MatchRepository
from app.models.match import Match as MatchORM, MatchStat as MatchStatORM

_SCALARS = ("opponent", "location", "home", "score_us", "score_them", "category", "notes")


def _to_domain(row: MatchORM) -> Match:
    return Match(
        id=row.id, school_id=row.school_id, date=row.date, opponent=row.opponent,
        location=row.location, home=row.home, score_us=row.score_us, score_them=row.score_them,
        category=row.category, notes=row.notes, created_at=row.created_at,
        stats=[
            MatchStatLine(
                id=s.id, student_id=s.student_id, goals=s.goals, assists=s.assists,
                yellow_cards=s.yellow_cards, red_cards=s.red_cards, rating=s.rating,
                played=s.played, notes=s.notes,
            )
            for s in row.stats
        ],
    )


class SqlAlchemyMatchRepository(MatchRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def next_stat_id(self) -> str:
        return str(uuid.uuid4())

    def add(self, match: Match) -> None:
        self.session.add(MatchORM(
            id=match.id, school_id=match.school_id, date=match.date, opponent=match.opponent,
            location=match.location, home=match.home, score_us=match.score_us,
            score_them=match.score_them, category=match.category, notes=match.notes,
        ))
        for s in match.stats:
            self.session.add(MatchStatORM(
                id=s.id, match_id=match.id, student_id=s.student_id, goals=s.goals,
                assists=s.assists, yellow_cards=s.yellow_cards, red_cards=s.red_cards,
                rating=s.rating, played=s.played, notes=s.notes,
            ))

    def save(self, match: Match) -> None:
        row = self.session.get(MatchORM, match.id)
        if row is None:
            return
        for field_name in _SCALARS:
            setattr(row, field_name, getattr(match, field_name))

    def get(self, match_id: str) -> Match | None:
        row = self.session.get(MatchORM, match_id)
        return _to_domain(row) if row else None

    def list_by_school(self, school_id: str) -> list[Match]:
        rows = (
            self.session.query(MatchORM)
            .filter(MatchORM.school_id == school_id)
            .order_by(MatchORM.date.desc())
            .all()
        )
        return [_to_domain(r) for r in rows]

    def remove(self, match: Match) -> None:
        # delete children first — the ORM has no cascade and match_id is NOT NULL
        self.session.query(MatchStatORM).filter(MatchStatORM.match_id == match.id).delete()
        row = self.session.get(MatchORM, match.id)
        if row:
            self.session.delete(row)
