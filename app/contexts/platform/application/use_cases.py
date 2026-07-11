from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.models.license import LicenseStatus
from app.models.user import UserRole
from app.contexts.platform.domain.tenant import School
from app.contexts.platform.domain.repositories import PlatformRepository
from app.contexts.platform.domain.read_models import StaffMember
from app.contexts.platform.application.dtos import SchoolView, LicenseView, SchoolDetailView

_SCHOOL_SCALARS = ("name", "primary_color", "active")
_LICENSE_SCALARS = ("plan", "status", "max_students", "max_coaches", "expires_at", "notes",
                    "family_included", "family_price_per_student", "family_seats")


class SchoolNotFound(DomainError):
    pass


class EmailAlreadyUsed(DomainError):
    pass


class StaffNotFound(DomainError):
    pass


class CoachLimitReached(DomainError):
    pass


def _require_school(repo: PlatformRepository, school_id: str) -> School:
    school = repo.get_school(school_id)
    if school is None:
        raise SchoolNotFound("Escolinha não encontrada")
    return school


# ── Escolas ───────────────────────────────────────────────────

class CreateSchool:
    def __init__(self, repo: PlatformRepository, uow: UnitOfWork):
        self.repo, self.uow = repo, uow

    def execute(self, *, name: str, primary_color: str = "#3b82f6") -> SchoolView:
        school = School.open(id=self.repo.next_id(), name=name,
                             primary_color=primary_color, license_id=self.repo.next_id())
        self.repo.add_school(school)
        self.uow.commit()
        return SchoolView.of(school)


class ListSchools:
    def __init__(self, repo: PlatformRepository):
        self.repo = repo

    def execute(self) -> list[SchoolView]:
        return [SchoolView.of(s) for s in self.repo.list_schools()]


class UpdateSchool:
    def __init__(self, repo: PlatformRepository, uow: UnitOfWork):
        self.repo, self.uow = repo, uow

    def execute(self, *, school_id: str, changes: dict) -> SchoolView:
        school = _require_school(self.repo, school_id)
        school.change_details(**{k: v for k, v in changes.items() if k in _SCHOOL_SCALARS and v is not None})
        self.repo.save_school(school)
        self.uow.commit()
        return SchoolView.of(school)


class GetSchoolDetail:
    def __init__(self, repo: PlatformRepository):
        self.repo = repo

    def execute(self, *, school_id: str) -> SchoolDetailView:
        school = _require_school(self.repo, school_id)
        manager_count, coach_count, student_count = self.repo.school_counts(school_id)
        active_students = self.repo.active_student_count(school_id)
        lic = school.license
        over_quota = bool(
            lic and lic.family_included and lic.family_seats is not None
            and active_students > lic.family_seats
        )
        return SchoolDetailView(
            school=SchoolView.of(school),
            license=LicenseView.of(school.id, school.license),
            manager_count=manager_count, coach_count=coach_count, student_count=student_count,
            active_student_count=active_students, family_over_quota=over_quota,
        )


class UpdateLicense:
    def __init__(self, repo: PlatformRepository, uow: UnitOfWork):
        self.repo, self.uow = repo, uow

    def execute(self, *, school_id: str, changes: dict) -> LicenseView:
        school = _require_school(self.repo, school_id)
        school.apply_license(license_id=self.repo.next_id(),
                             **{k: v for k, v in changes.items() if k in _LICENSE_SCALARS and v is not None})
        self.repo.save_school(school)
        self.uow.commit()
        return LicenseView.of(school.id, school.license)


# ── Staff (usuários da escola) ────────────────────────────────

class ListStaff:
    def __init__(self, repo: PlatformRepository):
        self.repo = repo

    def execute(self, *, school_id: str) -> list[StaffMember]:
        return self.repo.list_staff(school_id)


class CreateStaff:
    def __init__(self, repo: PlatformRepository, uow: UnitOfWork):
        self.repo, self.uow = repo, uow

    def execute(self, *, school_id: str, name: str, email: str,
                hashed_password: str, role: UserRole) -> StaffMember:
        school = _require_school(self.repo, school_id)
        if self.repo.email_exists(email):
            raise EmailAlreadyUsed("Email já cadastrado")
        if role == UserRole.coach and school.license is not None:
            if self.repo.coach_count(school_id) >= school.license.max_coaches:
                raise CoachLimitReached(
                    f"Limite de professores do plano atingido ({school.license.max_coaches}). "
                    "Faça upgrade para adicionar mais."
                )
        member = self.repo.add_staff(
            id=self.repo.next_id(), school_id=school_id, name=name, email=email,
            hashed_password=hashed_password, role=role,
        )
        self.uow.commit()
        return member


class DeleteStaff:
    def __init__(self, repo: PlatformRepository, uow: UnitOfWork):
        self.repo, self.uow = repo, uow

    def execute(self, *, school_id: str, user_id: str) -> None:
        member = self.repo.get_staff(user_id)
        if member is None or member.school_id != school_id:
            raise StaffNotFound("Usuário não encontrado")
        self.repo.remove_staff(user_id)
        self.uow.commit()


# ── Visão geral da plataforma ─────────────────────────────────

class PlatformOverview:
    def __init__(self, repo: PlatformRepository):
        self.repo = repo

    def execute(self) -> dict:
        return self.repo.platform_overview()
