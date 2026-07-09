from dataclasses import dataclass

from app.models.user import UserRole
from app.contexts.identity.domain.user import User


@dataclass
class UserView:
    id: str
    name: str
    email: str
    role: UserRole
    school_id: str | None

    @classmethod
    def of(cls, u: User) -> "UserView":
        return cls(id=u.id, name=u.name, email=u.email, role=u.role, school_id=u.school_id)
