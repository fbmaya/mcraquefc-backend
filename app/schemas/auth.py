from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.parent
    school_id: str | None = None


class GoogleLoginRequest(BaseModel):
    # ID token (JWT) emitido pelo Google Identity Services no front.
    credential: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    role: UserRole
    school_id: str | None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    school_id: str | None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole
    school_id: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: UserRole | None = None
    school_id: str | None = None
