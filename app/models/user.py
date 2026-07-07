from datetime import datetime
from sqlalchemy import String, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    platform_admin = "platform_admin"  # Meu Craque FC internal — manages schools/licenses
    manager        = "manager"         # School manager — full school ops + financial
    coach          = "coach"           # Coach — technical/sports, no financial access
    parent         = "parent"          # Parent/guardian — read-only on their child


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.id"))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    # Nullable: usuários que entram só via Google não têm senha local.
    hashed_password: Mapped[str | None] = mapped_column(String(200))
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.parent)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    school: Mapped["School | None"] = relationship(back_populates="users")
    parent_links: Mapped[list["ParentStudentLink"]] = relationship(back_populates="parent")
