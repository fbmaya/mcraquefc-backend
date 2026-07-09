import datetime as dt
from dataclasses import dataclass, field

from app.contexts.assessment.domain.evaluation import Evaluation, SKILLS


@dataclass
class NewEvaluation:
    student_id: str
    date: dt.date
    skills: dict = field(default_factory=dict)
    notes: str | None = None


@dataclass
class EvaluationView:
    id: str
    student_id: str
    evaluated_by: str | None
    date: dt.date | None
    notes: str | None
    created_at: dt.datetime | None
    # habilidades + eixos calculados
    passing: float | None
    finishing: float | None
    dribbling: float | None
    speed: float | None
    stamina: float | None
    agility: float | None
    positioning: float | None
    decision: float | None
    discipline: float | None
    teamwork: float | None
    attitude: float | None
    commitment: float | None
    leadership: float | None
    technique: float | None
    physical: float | None
    tactical: float | None
    mindset: float | None
    overall: float | None

    @classmethod
    def of(cls, e: Evaluation) -> "EvaluationView":
        return cls(
            id=e.id, student_id=e.student_id, evaluated_by=e.evaluated_by, date=e.date,
            notes=e.notes, created_at=e.created_at,
            technique=e.technique, physical=e.physical, tactical=e.tactical,
            mindset=e.mindset, overall=e.overall,
            **{k: getattr(e, k) for k in SKILLS},
        )
