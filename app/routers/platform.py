"""
/platform/* — Platform admin endpoints (Meu Craque FC internal team only).
Requires role=platform_admin on every route.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import date

from app.auth.deps import require_platform_admin
from app.auth.jwt import hash_password
from app.database import get_db
from app.models.user import User, UserRole
from app.models.school import School
from app.models.license import License, PlanType, LicenseStatus
from app.schemas.auth import UserOut, UserCreate
from app.services import licensing

router = APIRouter(prefix="/platform", tags=["platform"])


# ── Schemas (platform-specific) ──────────────────────────────

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


# ── Schools ───────────────────────────────────────────────────

@router.get("/schools", response_model=list[SchoolOut])
def list_schools(db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    return db.query(School).all()


@router.post("/schools", response_model=SchoolOut, status_code=status.HTTP_201_CREATED)
def create_school(
    body: SchoolCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
):
    school = School(id=str(uuid.uuid4()), name=body.name, primary_color=body.primary_color)
    db.add(school)
    db.flush()
    license_ = License(
        id=str(uuid.uuid4()),
        school_id=school.id,
        plan=PlanType.trial,
        status=LicenseStatus.active,
    )
    db.add(license_)
    db.commit()
    db.refresh(school)
    return school


@router.patch("/schools/{school_id}", response_model=SchoolOut)
def update_school(
    school_id: str,
    body: SchoolUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
):
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(school, field, value)
    db.commit()
    db.refresh(school)
    return school


@router.get("/schools/{school_id}", response_model=SchoolDetail)
def get_school_detail(
    school_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
):
    from app.models.student import Student

    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")
    users = db.query(User).filter(User.school_id == school_id).all()
    from app.models.student import Student
    student_count = db.query(Student).filter(Student.school_id == school_id).count()
    return SchoolDetail(
        school=school,
        license=school.license,
        manager_count=sum(1 for u in users if u.role == UserRole.manager),
        coach_count=sum(1 for u in users if u.role == UserRole.coach),
        student_count=student_count,
    )


# ── Licenses ─────────────────────────────────────────────────

@router.patch("/schools/{school_id}/license", response_model=LicenseOut)
def update_license(
    school_id: str,
    body: LicenseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
):
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")
    if not school.license:
        lic = License(id=str(uuid.uuid4()), school_id=school_id)
        db.add(lic)
        db.flush()
        school.license = lic
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(school.license, field, value)
    # Sync school.active with license status
    school.active = school.license.status == LicenseStatus.active
    db.commit()
    db.refresh(school.license)
    return school.license


# ── Users (school staff management) ──────────────────────────

@router.get("/schools/{school_id}/users", response_model=list[UserOut])
def list_school_users(
    school_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
):
    return db.query(User).filter(User.school_id == school_id).all()


@router.post("/schools/{school_id}/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_school_user(
    school_id: str,
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
):
    if not db.get(School, school_id):
        raise HTTPException(status_code=404, detail="Escolinha não encontrada")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    if body.role == UserRole.coach:
        licensing.assert_can_add_coach(db, school_id)
    user = User(
        id=str(uuid.uuid4()),
        school_id=school_id,
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/schools/{school_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school_user(
    school_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
):
    user = db.get(User, user_id)
    if not user or user.school_id != school_id:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(user)
    db.commit()


# ── Platform-level overview ───────────────────────────────────

@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    from app.models.student import Student

    total_schools   = db.query(School).count()
    active_schools  = db.query(School).filter(School.active == True).count()
    total_students  = db.query(Student).count()
    total_users     = db.query(User).filter(User.role != UserRole.platform_admin).count()
    licenses_by_plan = {}
    for lic in db.query(License).all():
        licenses_by_plan[lic.plan] = licenses_by_plan.get(lic.plan, 0) + 1
    return {
        "total_schools":  total_schools,
        "active_schools": active_schools,
        "total_students": total_students,
        "total_users":    total_users,
        "licenses_by_plan": licenses_by_plan,
    }
