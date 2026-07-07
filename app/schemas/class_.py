from datetime import datetime
from typing import Literal
from pydantic import BaseModel

Turno = Literal["Manhã", "Tarde", "Noite"]


class ClassCreate(BaseModel):
    name: str
    age_group: str | None = None
    period: Turno | None = None
    schedule: str | None = None
    coach_id: str | None = None


class ClassUpdate(BaseModel):
    name: str | None = None
    age_group: str | None = None
    period: Turno | None = None
    schedule: str | None = None
    coach_id: str | None = None


class ClassOut(BaseModel):
    id: str
    school_id: str
    name: str
    age_group: str | None
    period: str | None
    schedule: str | None
    coach_id: str | None
    student_ids: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class EnrollmentCreate(BaseModel):
    student_id: str


class EnrollmentOut(BaseModel):
    id: str
    class_id: str
    student_id: str
    active: bool

    model_config = {"from_attributes": True}
