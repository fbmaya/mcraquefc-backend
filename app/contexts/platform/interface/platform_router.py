"""
/platform/* — Endpoints de administração da plataforma (equipe interna Meu Craque FC).
Exige role=platform_admin em todas as rotas.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.deps import require_platform_admin
from app.auth.jwt import hash_password
from app.models.user import User, UserRole
from app.models.license import PlanType, LicenseStatus
from app.schemas.auth import UserOut, UserCreate
from app.contexts.platform.application import use_cases as uc
from app.contexts.platform.interface import deps

router = APIRouter(prefix="/platform", tags=["platform"])


# ── Schemas (específicos da plataforma) ──────────────────────

class SchoolCreate(BaseModel):
    name: str
    primary_color: str = "#3b82f6"


class SchoolUpdate(BaseModel):
    name: str | None = None
    primary_color: str | None = None
    active: bool | None = None


class SchoolOut(BaseModel):
    id: str
    name: str
    primary_color: str
    active: bool

    model_config = {"from_attributes": True}


class LicenseUpdate(BaseModel):
    plan: PlanType | None = None
    status: LicenseStatus | None = None
    max_students: int | None = None
    max_coaches: int | None = None
    expires_at: date | None = None
    notes: str | None = None


class LicenseOut(BaseModel):
    id: str
    school_id: str
    plan: PlanType
    status: LicenseStatus
    max_students: int
    max_coaches: int
    expires_at: date | None
    notes: str | None

    model_config = {"from_attributes": True}


class SchoolDetail(BaseModel):
    school: SchoolOut
    license: LicenseOut | None
    manager_count: int
    coach_count: int
    student_count: int

    model_config = {"from_attributes": True}


# ── Escolas ───────────────────────────────────────────────────

@router.get("/schools", response_model=list[SchoolOut])
def list_schools(repo=Depends(deps.platform_repo), _: User = Depends(require_platform_admin)):
    return uc.ListSchools(repo).execute()


@router.post("/schools", response_model=SchoolOut, status_code=status.HTTP_201_CREATED)
def create_school(body: SchoolCreate, repo=Depends(deps.platform_repo), uow=Depends(deps.uow),
                  _: User = Depends(require_platform_admin)):
    return uc.CreateSchool(repo, uow).execute(name=body.name, primary_color=body.primary_color)


@router.patch("/schools/{school_id}", response_model=SchoolOut)
def update_school(school_id: str, body: SchoolUpdate, repo=Depends(deps.platform_repo),
                  uow=Depends(deps.uow), _: User = Depends(require_platform_admin)):
    try:
        return uc.UpdateSchool(repo, uow).execute(
            school_id=school_id, changes=body.model_dump(exclude_unset=True))
    except uc.SchoolNotFound:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")


@router.get("/schools/{school_id}", response_model=SchoolDetail)
def get_school_detail(school_id: str, repo=Depends(deps.platform_repo),
                      _: User = Depends(require_platform_admin)):
    try:
        return uc.GetSchoolDetail(repo).execute(school_id=school_id)
    except uc.SchoolNotFound:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")


# ── Licenças ─────────────────────────────────────────────────

@router.patch("/schools/{school_id}/license", response_model=LicenseOut)
def update_license(school_id: str, body: LicenseUpdate, repo=Depends(deps.platform_repo),
                   uow=Depends(deps.uow), _: User = Depends(require_platform_admin)):
    try:
        return uc.UpdateLicense(repo, uow).execute(
            school_id=school_id, changes=body.model_dump(exclude_unset=True))
    except uc.SchoolNotFound:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")


# ── Usuários (staff da escola) ───────────────────────────────

@router.get("/schools/{school_id}/users", response_model=list[UserOut])
def list_school_users(school_id: str, repo=Depends(deps.platform_repo),
                      _: User = Depends(require_platform_admin)):
    return uc.ListStaff(repo).execute(school_id=school_id)


@router.post("/schools/{school_id}/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_school_user(school_id: str, body: UserCreate, repo=Depends(deps.platform_repo),
                       uow=Depends(deps.uow), _: User = Depends(require_platform_admin)):
    try:
        return uc.CreateStaff(repo, uow).execute(
            school_id=school_id, name=body.name, email=body.email,
            hashed_password=hash_password(body.password), role=body.role)
    except uc.SchoolNotFound:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")
    except uc.EmailAlreadyUsed:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    except uc.CoachLimitReached as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/schools/{school_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school_user(school_id: str, user_id: str, repo=Depends(deps.platform_repo),
                       uow=Depends(deps.uow), _: User = Depends(require_platform_admin)):
    try:
        uc.DeleteStaff(repo, uow).execute(school_id=school_id, user_id=user_id)
    except uc.StaffNotFound:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")


# ── Visão geral da plataforma ─────────────────────────────────

@router.get("/overview")
def overview(repo=Depends(deps.platform_repo), _: User = Depends(require_platform_admin)):
    return uc.PlatformOverview(repo).execute()
