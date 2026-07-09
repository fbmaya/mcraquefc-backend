from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.contexts.performance.domain.match import Match, MatchStatLine
from app.contexts.performance.domain.repositories import MatchRepository
from app.contexts.performance.application.matches_dtos import NewMatch, MatchView

_SCALARS = ("opponent", "location", "home", "score_us", "score_them", "category", "notes")


class MatchNotFound(DomainError):
    pass


def _require(matches: MatchRepository, school_id: str, match_id: str) -> Match:
    m = matches.get(match_id)
    if m is None or m.school_id != school_id:
        raise MatchNotFound("Jogo não encontrado")
    return m


class CreateMatch:
    def __init__(self, matches: MatchRepository, uow: UnitOfWork):
        self.matches, self.uow = matches, uow

    def execute(self, *, school_id: str, data: NewMatch) -> MatchView:
        lines = [
            MatchStatLine(
                id=self.matches.next_stat_id(), student_id=s.student_id, goals=s.goals,
                assists=s.assists, yellow_cards=s.yellow_cards, red_cards=s.red_cards,
                rating=s.rating, played=s.played, notes=s.notes,
            )
            for s in data.stats
        ]
        match = Match.register(
            id=self.matches.next_id(), school_id=school_id, date=data.date, opponent=data.opponent,
            home=data.home, location=data.location, score_us=data.score_us,
            score_them=data.score_them, category=data.category, notes=data.notes, stats=lines,
        )
        self.matches.add(match)
        self.uow.commit()
        saved = self.matches.get(match.id)  # relê p/ created_at
        return MatchView.of(saved)


class UpdateMatch:
    def __init__(self, matches: MatchRepository, uow: UnitOfWork):
        self.matches, self.uow = matches, uow

    def execute(self, *, school_id: str, match_id: str, changes: dict) -> MatchView:
        match = _require(self.matches, school_id, match_id)
        fields = {k: v for k, v in changes.items() if k in _SCALARS and v is not None}
        match.change_fields(**fields)
        self.matches.save(match)  # persiste (lição da Fase 1)
        self.uow.commit()
        return MatchView.of(match)


class ListMatches:
    def __init__(self, matches: MatchRepository):
        self.matches = matches

    def execute(self, *, school_id: str) -> list[MatchView]:
        return [MatchView.of(m) for m in self.matches.list_by_school(school_id)]


class DeleteMatch:
    def __init__(self, matches: MatchRepository, uow: UnitOfWork):
        self.matches, self.uow = matches, uow

    def execute(self, *, school_id: str, match_id: str) -> None:
        self.matches.remove(_require(self.matches, school_id, match_id))
        self.uow.commit()
