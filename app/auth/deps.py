from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.database import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error

    # Block staff of an inactive school / suspended license on every request.
    # Imported here to avoid a circular import at module load.
    from app.services import licensing
    licensing.assert_tenant_active(db, user)

    return user


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Meu Craque FC internal team only."""
    if current_user.role != UserRole.platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito à equipe da plataforma")
    return current_user


def require_manager(current_user: User = Depends(get_current_user)) -> User:
    """School manager only — full school ops."""
    if current_user.role not in (UserRole.manager, UserRole.platform_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao gestor da escolinha")
    return current_user


def require_coach_or_manager(current_user: User = Depends(get_current_user)) -> User:
    """Coach or manager — technical/sports operations."""
    if current_user.role not in (UserRole.coach, UserRole.manager, UserRole.platform_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a professores e gestores")
    return current_user


def require_parent(current_user: User = Depends(get_current_user)) -> User:
    """Parent/guardian only."""
    if current_user.role != UserRole.parent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a responsáveis")
    return current_user


# Legacy alias kept so existing routers don't break before we update them
require_admin = require_manager
