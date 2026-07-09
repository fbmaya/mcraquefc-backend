from abc import ABC, abstractmethod

from app.models.user import UserRole
from app.contexts.platform.domain.tenant import School
from app.contexts.platform.domain.read_models import StaffMember


class PlatformRepository(ABC):
    def next_id(self) -> str: ...

    # ── Escolas / licenças ──────────────────────────────────────
    @abstractmethod
    def add_school(self, school: School) -> None: ...
    @abstractmethod
    def get_school(self, school_id: str) -> School | None: ...
    @abstractmethod
    def list_schools(self) -> list[School]: ...
    @abstractmethod
    def save_school(self, school: School) -> None: ...

    # ── Contadores / visão geral ────────────────────────────────
    @abstractmethod
    def school_counts(self, school_id: str) -> tuple[int, int, int]:
        """(manager_count, coach_count, student_count)"""
    @abstractmethod
    def coach_count(self, school_id: str) -> int: ...
    @abstractmethod
    def platform_overview(self) -> dict: ...

    # ── Staff (usuários da escola) ──────────────────────────────
    @abstractmethod
    def list_staff(self, school_id: str) -> list[StaffMember]: ...
    @abstractmethod
    def get_staff(self, user_id: str) -> StaffMember | None: ...
    @abstractmethod
    def email_exists(self, email: str) -> bool: ...
    @abstractmethod
    def add_staff(self, *, id: str, school_id: str, name: str, email: str,
                  hashed_password: str, role: UserRole) -> StaffMember: ...
    @abstractmethod
    def remove_staff(self, user_id: str) -> None: ...
