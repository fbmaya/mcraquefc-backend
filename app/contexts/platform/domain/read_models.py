from dataclasses import dataclass

from app.models.user import UserRole


@dataclass
class StaffMember:
    id: str
    name: str
    email: str
    role: UserRole
    school_id: str | None
