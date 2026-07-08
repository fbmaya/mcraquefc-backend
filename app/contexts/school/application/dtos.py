import datetime as dt
from dataclasses import dataclass

from app.contexts.school.domain.school_class import SchoolClass


@dataclass
class NewClass:
    name: str
    age_group: str | None = None
    period: str | None = None
    schedule: str | None = None
    coach_id: str | None = None


@dataclass
class ClassView:
    id: str
    school_id: str
    name: str
    age_group: str | None
    period: str | None
    schedule: str | None
    coach_id: str | None
    student_ids: list[str]
    created_at: dt.datetime | None

    @classmethod
    def of(cls, c: SchoolClass, student_ids: list[str]) -> "ClassView":
        return cls(
            id=c.id, school_id=c.school_id, name=c.name, age_group=c.age_group,
            period=c.period, schedule=c.schedule, coach_id=c.coach_id,
            student_ids=student_ids, created_at=c.created_at,
        )


@dataclass
class EnrollmentView:
    id: str
    class_id: str
    student_id: str
    active: bool
