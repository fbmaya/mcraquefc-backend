import datetime as dt
from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot
from app.shared.domain.errors import ValidationError
from app.models.user import UserRole  # vocabulário compartilhado


@dataclass(eq=False)
class User(AggregateRoot):
    name: str = ""
    email: str = ""
    hashed_password: str | None = None
    google_sub: str | None = None
    role: UserRole = UserRole.parent
    school_id: str | None = None
    created_at: dt.datetime | None = None

    @classmethod
    def register_parent(cls, *, id: str, name: str, email: str, hashed_password: str) -> "User":
        """Cadastro público: apenas responsáveis, sem escola vinculada."""
        if not name or not name.strip():
            raise ValidationError("Nome é obrigatório")
        if not email:
            raise ValidationError("Email é obrigatório")
        return cls(id=id, name=name.strip(), email=email, hashed_password=hashed_password,
                   role=UserRole.parent, school_id=None)

    @classmethod
    def provision_google_parent(cls, *, id: str, name: str, email: str, google_sub: str | None) -> "User":
        """Email desconhecido no login Google → responsável auto-provisionado (sem senha)."""
        return cls(id=id, name=name, email=email, hashed_password=None, google_sub=google_sub,
                   role=UserRole.parent, school_id=None)

    def link_google(self, sub: str | None) -> bool:
        """Vincula o google_sub se ainda não houver. Retorna se mudou."""
        if sub and not self.google_sub:
            self.google_sub = sub
            return True
        return False
