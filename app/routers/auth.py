import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.jwt import hash_password, verify_password, create_access_token
from app.auth.deps import get_current_user
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Public registration is for guardians (parents) only. Staff accounts
    # (manager/coach) are tenant-bound and created by a platform_admin via
    # /platform/schools/{id}/users — never through the open endpoint, which
    # would otherwise let anyone join an arbitrary school.
    if body.role != UserRole.parent:
        raise HTTPException(
            status_code=403,
            detail="Registro público disponível apenas para responsáveis. Gestores e professores são cadastrados pela plataforma.",
        )

    user = User(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.parent,
        school_id=None,  # parents are not bound to a single school
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role, "school_id": user.school_id})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        role=user.role,
        school_id=user.school_id,
    )


@router.post("/token", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # refuse login early for staff of an inactive/suspended tenant
    from app.services import licensing
    licensing.assert_tenant_active(db, user)
    token = create_access_token({"sub": user.id, "role": user.role, "school_id": user.school_id})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        role=user.role,
        school_id=user.school_id,
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
