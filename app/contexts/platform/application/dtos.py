import datetime as dt
from dataclasses import dataclass

from app.models.license import PlanType, LicenseStatus
from app.contexts.platform.domain.tenant import School, License


@dataclass
class SchoolView:
    id: str
    name: str
    primary_color: str
    active: bool

    @classmethod
    def of(cls, s: School) -> "SchoolView":
        return cls(id=s.id, name=s.name, primary_color=s.primary_color, active=s.active)


@dataclass
class LicenseView:
    id: str
    school_id: str
    plan: PlanType
    status: LicenseStatus
    max_students: int
    max_coaches: int
    expires_at: dt.date | None
    notes: str | None

    @classmethod
    def of(cls, school_id: str, lic: License | None) -> "LicenseView | None":
        if lic is None:
            return None
        return cls(
            id=lic.id, school_id=school_id, plan=lic.plan, status=lic.status,
            max_students=lic.max_students, max_coaches=lic.max_coaches,
            expires_at=lic.expires_at, notes=lic.notes,
        )


@dataclass
class SchoolDetailView:
    school: SchoolView
    license: LicenseView | None
    manager_count: int
    coach_count: int
    student_count: int
