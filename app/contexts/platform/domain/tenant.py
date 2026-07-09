import datetime as dt
from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError
# Vocabulário compartilhado (str-enums sem comportamento): reusados dos models.
from app.models.license import PlanType, LicenseStatus

_SCHOOL_SCALARS = ("name", "primary_color", "active")
_LICENSE_SCALARS = ("plan", "status", "max_students", "max_coaches", "expires_at", "notes")


@dataclass
class License:
    id: str
    plan: PlanType = PlanType.trial
    status: LicenseStatus = LicenseStatus.active
    max_students: int = 30
    max_coaches: int = 2
    expires_at: dt.date | None = None
    notes: str | None = None


@dataclass(eq=False)
class School(AggregateRoot):
    """Raiz do contexto Tenancy: escolinha + sua licença (1:1)."""
    name: str = ""
    primary_color: str = "#3b82f6"
    active: bool = True
    created_at: dt.datetime | None = None
    license: License | None = None

    @classmethod
    def open(cls, *, id: str, name: str, license_id: str,
             primary_color: str = "#3b82f6") -> "School":
        if not name or not name.strip():
            raise ValidationError("Nome da escolinha é obrigatório")
        return cls(
            id=id, name=name.strip(), primary_color=primary_color, active=True,
            license=License(id=license_id, plan=PlanType.trial, status=LicenseStatus.active),
        )

    def change_details(self, **fields) -> None:
        for key, value in fields.items():
            if key in _SCHOOL_SCALARS:
                setattr(self, key, value)

    def apply_license(self, *, license_id: str, **fields) -> None:
        """Cria (se não existir) e atualiza a licença; sincroniza `active` com o status."""
        if self.license is None:
            self.license = License(id=license_id)
        for key, value in fields.items():
            if key in _LICENSE_SCALARS:
                setattr(self.license, key, value)
        self.active = self.license.status == LicenseStatus.active
