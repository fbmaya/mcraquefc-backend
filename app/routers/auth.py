import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.jwt import hash_password, verify_password, create_access_token
from app.auth.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import GoogleLoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.parent_linking import reconcile_parent_links

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    token = create_access_token({"sub": user.id, "role": user.role, "school_id": user.school_id})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        role=user.role,
        school_id=user.school_id,
    )


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

    reconcile_parent_links(db, user)
    return _token_response(user)


@router.post("/token", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not user.hashed_password or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # refuse login early for staff of an inactive/suspended tenant
    from app.contexts.platform.application import licensing
    licensing.assert_tenant_active(db, user)
    reconcile_parent_links(db, user)
    return _token_response(user)


@router.post("/google", response_model=TokenResponse)
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Login com Google (painel). Verifica o ID token, acha/cria o usuário por
    email e emite o JWT próprio. Email novo é auto-provisionado como responsável;
    emails já existentes (inclusive staff pré-cadastrado) entram com seu papel."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Login com Google não configurado")

    # Import local: a lib google-auth só é necessária neste endpoint.
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    try:
        info = google_id_token.verify_oauth2_token(
            body.credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token do Google inválido")

    if not info.get("email") or not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email do Google não verificado")

    email = info["email"].strip().lower()
    sub = info.get("sub")
    name = info.get("name") or email

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        # Email desconhecido → auto-provisiona como responsável (parent).
        user = User(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            hashed_password=None,
            google_sub=sub,
            role=UserRole.parent,
            school_id=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif sub and not user.google_sub:
        user.google_sub = sub
        db.commit()

    # staff de escola inativa/licença suspensa é barrado (ignora parent/platform_admin)
    from app.contexts.platform.application import licensing
    licensing.assert_tenant_active(db, user)
    reconcile_parent_links(db, user)
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
