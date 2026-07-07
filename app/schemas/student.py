from datetime import date, datetime
from pydantic import BaseModel, EmailStr


class StudentCreate(BaseModel):
    name: str
    # E-mail do responsável é obrigatório: serve como login de acesso do responsável.
    guardian_email: EmailStr
    birth_date: date | None = None
    position: str | None = None
    foot: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    notes: str | None = None


class StudentUpdate(BaseModel):
    name: str | None = None
    birth_date: date | None = None
    position: str | None = None
    foot: str | None = None
    guardian_name: str | None = None
    guardian_email: EmailStr | None = None
    guardian_phone: str | None = None
    notes: str | None = None
    photo_url: str | None = None


class StudentOut(BaseModel):
    id: str
    school_id: str
    name: str
    birth_date: date | None
    photo_url: str | None
    position: str | None
    foot: str | None
    guardian_name: str | None
    guardian_email: str | None
    guardian_phone: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
