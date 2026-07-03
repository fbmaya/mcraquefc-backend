from datetime import date, datetime
from pydantic import BaseModel, Field


class EvaluationCreate(BaseModel):
    student_id: str
    date: date

    # Technical
    passing: float | None = Field(None, ge=0, le=10)
    finishing: float | None = Field(None, ge=0, le=10)
    dribbling: float | None = Field(None, ge=0, le=10)
    # Physical
    speed: float | None = Field(None, ge=0, le=10)
    stamina: float | None = Field(None, ge=0, le=10)
    agility: float | None = Field(None, ge=0, le=10)
    # Tactical
    positioning: float | None = Field(None, ge=0, le=10)
    decision: float | None = Field(None, ge=0, le=10)
    # Behavioral / mental
    discipline: float | None = Field(None, ge=0, le=10)
    teamwork: float | None = Field(None, ge=0, le=10)
    attitude: float | None = Field(None, ge=0, le=10)
    commitment: float | None = Field(None, ge=0, le=10)
    leadership: float | None = Field(None, ge=0, le=10)

    notes: str | None = None


class EvaluationOut(BaseModel):
    id: str
    student_id: str
    evaluated_by: str | None
    date: date

    # Granular skills
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

    # Summary axes (computed on the model)
    technique: float | None
    physical: float | None
    tactical: float | None
    mindset: float | None
    overall: float | None

    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
