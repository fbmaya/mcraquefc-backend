from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class School(Base):
    __tablename__ = "schools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    primary_color: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="school")
    students: Mapped[list["Student"]] = relationship(back_populates="school")
    classes: Mapped[list["Class"]] = relationship(back_populates="school")
    matches: Mapped[list["Match"]] = relationship(back_populates="school")
    license: Mapped["License | None"] = relationship(back_populates="school", uselist=False)
