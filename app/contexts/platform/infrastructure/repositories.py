import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.school import School as SchoolORM
from app.models.license import License as LicenseORM
from app.models.student import Student as StudentORM
from app.models.user import User as UserORM, UserRole
from app.contexts.platform.domain.tenant import School, License
from app.contexts.platform.domain.read_models import StaffMember
from app.contexts.platform.domain.repositories import PlatformRepository

_SCHOOL_SCALARS = ("name", "primary_color", "active")
_LICENSE_SCALARS = ("plan", "status", "max_students", "max_coaches", "expires_at", "notes",
                    "family_included", "family_price_per_student", "family_seats")


def _to_domain(row: SchoolORM) -> School:
    lic = None
    if row.license is not None:
        lic = License(
            id=row.license.id, plan=row.license.plan, status=row.license.status,
            max_students=row.license.max_students, max_coaches=row.license.max_coaches,
            family_included=row.license.family_included,
            family_price_per_student=row.license.family_price_per_student,
            family_seats=row.license.family_seats,
            expires_at=row.license.expires_at, notes=row.license.notes,
        )
    return School(
        id=row.id, name=row.name, primary_color=row.primary_color, active=row.active,
        created_at=row.created_at, license=lic,
    )


def _staff(row: UserORM) -> StaffMember:
    return StaffMember(id=row.id, name=row.name, email=row.email, role=row.role, school_id=row.school_id)


class SqlAlchemyPlatformRepository(PlatformRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    # ── Escolas / licenças ──────────────────────────────────────

    def add_school(self, school: School) -> None:
        self.session.add(SchoolORM(
            id=school.id, name=school.name, primary_color=school.primary_color, active=school.active,
        ))
        if school.license is not None:
            self.session.add(LicenseORM(
                id=school.license.id, school_id=school.id,
                **{k: getattr(school.license, k) for k in _LICENSE_SCALARS},
            ))

    def get_school(self, school_id: str) -> School | None:
        row = self.session.get(SchoolORM, school_id)
        return _to_domain(row) if row else None

    def list_schools(self) -> list[School]:
        return [_to_domain(r) for r in self.session.query(SchoolORM).all()]

    def save_school(self, school: School) -> None:
        row = self.session.get(SchoolORM, school.id)
        if row is None:
            return
        for field_name in _SCHOOL_SCALARS:
            setattr(row, field_name, getattr(school, field_name))
        if school.license is not None:
            # licença é 1:1 com a escola — upsert por school_id
            lic = self.session.query(LicenseORM).filter(LicenseORM.school_id == school.id).first()
            if lic is None:
                lic = LicenseORM(id=school.license.id, school_id=school.id)
                self.session.add(lic)
            for field_name in _LICENSE_SCALARS:
                setattr(lic, field_name, getattr(school.license, field_name))

    # ── Contadores / visão geral ────────────────────────────────

    def school_counts(self, school_id: str) -> tuple[int, int, int]:
        managers = (
            self.session.query(func.count(UserORM.id))
            .filter(UserORM.school_id == school_id, UserORM.role == UserRole.manager).scalar()
        ) or 0
        coaches = (
            self.session.query(func.count(UserORM.id))
            .filter(UserORM.school_id == school_id, UserORM.role == UserRole.coach).scalar()
        ) or 0
        students = (
            self.session.query(func.count(StudentORM.id))
            .filter(StudentORM.school_id == school_id).scalar()
        ) or 0
        return int(managers), int(coaches), int(students)

    def coach_count(self, school_id: str) -> int:
        return (
            self.session.query(func.count(UserORM.id))
            .filter(UserORM.school_id == school_id, UserORM.role == UserRole.coach).scalar()
        ) or 0

    def active_student_count(self, school_id: str) -> int:
        return (
            self.session.query(func.count(StudentORM.id))
            .filter(StudentORM.school_id == school_id, StudentORM.active == True).scalar()  # noqa: E712
        ) or 0

    def platform_overview(self) -> dict:
        total_schools = self.session.query(func.count(SchoolORM.id)).scalar() or 0
        active_schools = (
            self.session.query(func.count(SchoolORM.id)).filter(SchoolORM.active == True).scalar()  # noqa: E712
        ) or 0
        total_students = self.session.query(func.count(StudentORM.id)).scalar() or 0
        total_users = (
            self.session.query(func.count(UserORM.id))
            .filter(UserORM.role != UserRole.platform_admin).scalar()
        ) or 0
        licenses_by_plan: dict = {}
        for lic in self.session.query(LicenseORM).all():
            licenses_by_plan[lic.plan] = licenses_by_plan.get(lic.plan, 0) + 1
        return {
            "total_schools": int(total_schools),
            "active_schools": int(active_schools),
            "total_students": int(total_students),
            "total_users": int(total_users),
            "licenses_by_plan": licenses_by_plan,
        }

    # ── Staff ───────────────────────────────────────────────────

    def list_staff(self, school_id: str) -> list[StaffMember]:
        rows = self.session.query(UserORM).filter(UserORM.school_id == school_id).all()
        return [_staff(r) for r in rows]

    def get_staff(self, user_id: str) -> StaffMember | None:
        row = self.session.get(UserORM, user_id)
        return _staff(row) if row else None

    def email_exists(self, email: str) -> bool:
        return self.session.query(UserORM.id).filter(UserORM.email == email).first() is not None

    def add_staff(self, *, id: str, school_id: str, name: str, email: str,
                  hashed_password: str, role: UserRole) -> StaffMember:
        row = UserORM(id=id, school_id=school_id, name=name, email=email,
                      hashed_password=hashed_password, role=role)
        self.session.add(row)
        return _staff(row)

    def remove_staff(self, user_id: str) -> None:
        row = self.session.get(UserORM, user_id)
        if row:
            self.session.delete(row)
