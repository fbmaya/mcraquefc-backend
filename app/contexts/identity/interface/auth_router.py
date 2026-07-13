from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.jwt import hash_password, create_access_token
from app.auth.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.school import School
from app.schemas.auth import GoogleLoginRequest, RegisterRequest, TokenResponse, UserOut
from app.contexts.identity.application import use_cases as uc
from app.contexts.identity.application.dtos import UserView
from app.contexts.identity.interface import deps
# guard de tenancy (idioma publicado do contexto Platform)
from app.contexts.platform.application import licensing

router = APIRouter(prefix="/auth", tags=["auth"])


def _school_name(db: Session, school_id: str | None) -> str | None:
    if not school_id:
        return None
    school = db.get(School, school_id)
    return school.name if school else None


def _token_response(view: UserView, school_name: str | None = None) -> TokenResponse:
    token = create_access_token({"sub": view.id, "role": view.role, "school_id": view.school_id})
    return TokenResponse(
        access_token=token, user_id=view.id, name=view.name,
        role=view.role, school_id=view.school_id, school_name=school_name,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, users=Depends(deps.user_repo),
             links=Depends(deps.link_repo), uow=Depends(deps.uow)):
    # Registro público é só para responsáveis. Staff (manager/coach) é tenant-bound
    # e criado por platform_admin via /platform/schools/{id}/users.
    try:
        view = uc.RegisterParent(users, links, uow).execute(
            name=body.name, email=body.email,
            hashed_password=hash_password(body.password), role=body.role)
    except uc.EmailAlreadyUsed:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    except uc.PublicRegistrationParentOnly as e:
        raise HTTPException(status_code=403, detail=str(e))
    return _token_response(view)


@router.post("/token", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db),
          users=Depends(deps.user_repo), links=Depends(deps.link_repo), uow=Depends(deps.uow)):
    try:
        view = uc.AuthenticatePassword(users).execute(email=form.username, password=form.password)
    except uc.InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # barra login de staff de tenant inativo/suspenso antes de reconciliar
    licensing.assert_tenant_active(db, view)
    uc.ReconcileParentLinks(links, uow).execute(user_id=view.id, email=view.email, role=view.role)
    return _token_response(view, _school_name(db, view.school_id))


@router.post("/google", response_model=TokenResponse)
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db),
                 users=Depends(deps.user_repo), links=Depends(deps.link_repo), uow=Depends(deps.uow)):
    """Login com Google (painel). Verifica o ID token, acha/cria o usuário por
    email e emite o JWT próprio. Email novo é auto-provisionado como responsável."""
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
    view = uc.GoogleUpsert(users, uow).execute(
        email=email, sub=info.get("sub"), name=info.get("name") or email)

    licensing.assert_tenant_active(db, view)
    uc.ReconcileParentLinks(links, uow).execute(user_id=view.id, email=view.email, role=view.role)
    return _token_response(view, _school_name(db, view.school_id))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
