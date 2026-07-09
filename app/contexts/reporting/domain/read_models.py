import datetime as dt
from dataclasses import dataclass

# Ordem importa: é a ordem dos eixos do radar (espelha o frontend).
SUMMARY_AXES = ["technique", "physical", "tactical", "mindset", "discipline", "teamwork"]


@dataclass
class StudentRef:
    id: str
    name: str
    position: str | None
    school_id: str


@dataclass
class EvalSnapshot:
    date: dt.date | None
    overall: float | None
    axes: list[float | None]   # valores na ordem de SUMMARY_AXES
