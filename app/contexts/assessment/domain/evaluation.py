import datetime as dt
from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError

# Habilidades granulares (0-10). A validação de faixa fica no schema Pydantic.
SKILLS = (
    "passing", "finishing", "dribbling",       # técnica
    "speed", "stamina", "agility",             # físico
    "positioning", "decision",                 # tático
    "discipline", "teamwork", "attitude", "commitment", "leadership",  # comportamental
)


def _avg(*values: float | None) -> float | None:
    """Média das notas informadas, ignorando None. None se todas forem None."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 1)


@dataclass(eq=False)
class Evaluation(AggregateRoot):
    student_id: str = ""
    date: dt.date | None = None
    evaluated_by: str | None = None
    notes: str | None = None
    created_at: dt.datetime | None = None
    # habilidades
    passing: float | None = None
    finishing: float | None = None
    dribbling: float | None = None
    speed: float | None = None
    stamina: float | None = None
    agility: float | None = None
    positioning: float | None = None
    decision: float | None = None
    discipline: float | None = None
    teamwork: float | None = None
    attitude: float | None = None
    commitment: float | None = None
    leadership: float | None = None

    @classmethod
    def register(cls, *, id: str, student_id: str, date: dt.date, skills: dict,
                 evaluated_by: str | None = None, notes: str | None = None) -> "Evaluation":
        if not student_id:
            raise ValidationError("Aluno é obrigatório")
        if date is None:
            raise ValidationError("Data é obrigatória")
        return cls(
            id=id, student_id=student_id, date=date, evaluated_by=evaluated_by, notes=notes,
            **{k: skills.get(k) for k in SKILLS},
        )

    # ── Eixos-resumo (calculados, exibidos no radar) ──────────────
    @property
    def technique(self) -> float | None:
        return _avg(self.passing, self.finishing, self.dribbling)

    @property
    def physical(self) -> float | None:
        return _avg(self.speed, self.stamina, self.agility)

    @property
    def tactical(self) -> float | None:
        return _avg(self.positioning, self.decision)

    @property
    def mindset(self) -> float | None:
        return _avg(self.attitude, self.commitment)

    @property
    def overall(self) -> float | None:
        """Nota 0-10 única sobre todas as habilidades registradas."""
        return _avg(*(getattr(self, k) for k in SKILLS))
