import uuid

from sqlalchemy.orm import Session

from app.models.family_subscription import FamilySubscription as SubORM, FamilySubStatus
from app.models.student import Student as StudentORM
from app.models.school import School as SchoolORM
from app.models.license import License as LicenseORM, LicenseStatus
from app.models.parent_link import ParentStudentLink as LinkORM
from app.contexts.family.domain.subscription import FamilySubscription
from app.contexts.family.domain.repositories import (
    FamilySubscriptionRepository, FamilyAccessReader, StudentAccessInfo,
)

_SCALARS = ("status", "price_tier", "current_period", "expires_at")


def _to_domain(row: SubORM) -> FamilySubscription:
    return FamilySubscription(
        id=row.id, parent_id=row.parent_id, school_id=row.school_id, status=row.status,
        price_tier=row.price_tier, current_period=row.current_period, expires_at=row.expires_at,
        created_at=row.created_at, updated_at=row.updated_at,
    )


class SqlAlchemyFamilySubscriptionRepository(FamilySubscriptionRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def add(self, sub: FamilySubscription) -> None:
        self.session.add(SubORM(
            id=sub.id, parent_id=sub.parent_id, school_id=sub.school_id, status=sub.status,
            price_tier=sub.price_tier, current_period=sub.current_period, expires_at=sub.expires_at,
        ))

    def save(self, sub: FamilySubscription) -> None:
        row = self.session.get(SubORM, sub.id)
        if row is None:
            return
        for field_name in _SCALARS:
            setattr(row, field_name, getattr(sub, field_name))

    def get(self, sub_id: str) -> FamilySubscription | None:
        row = self.session.get(SubORM, sub_id)
        return _to_domain(row) if row else None

    def active_for(self, parent_id: str, school_id: str) -> FamilySubscription | None:
        # "ativa" aqui = não-cancelada (o vencimento é avaliado por covers() no gate)
        row = (
            self.session.query(SubORM)
            .filter(
                SubORM.parent_id == parent_id,
                SubORM.school_id == school_id,
                SubORM.status != FamilySubStatus.cancelled,
            )
            .order_by(SubORM.created_at.desc())
            .first()
        )
        return _to_domain(row) if row else None

    def list_by_school(self, school_id: str) -> list[FamilySubscription]:
        rows = (
            self.session.query(SubORM)
            .filter(SubORM.school_id == school_id)
            .order_by(SubORM.created_at.desc())
            .all()
        )
        return [_to_domain(r) for r in rows]


class SqlAlchemyFamilyAccessReader(FamilyAccessReader):
    def __init__(self, session: Session):
        self.session = session

    def is_linked(self, parent_id: str, student_id: str) -> bool:
        return (
            self.session.query(LinkORM.id)
            .filter(LinkORM.parent_id == parent_id, LinkORM.student_id == student_id)
            .first()
            is not None
        )

    def student_access_info(self, student_id: str) -> StudentAccessInfo | None:
        row = self.session.get(StudentORM, student_id)
        if row is None:
            return None
        return StudentAccessInfo(active=row.active, school_id=row.school_id)

    def school_family_included(self, school_id: str) -> bool:
        school = self.session.get(SchoolORM, school_id)
        if school is None or not school.active:
            return False
        lic = self.session.query(LicenseORM).filter(LicenseORM.school_id == school_id).first()
        return lic is not None and lic.family_included and lic.status == LicenseStatus.active
