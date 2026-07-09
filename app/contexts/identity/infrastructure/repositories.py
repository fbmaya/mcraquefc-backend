import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User as UserORM
from app.models.student import Student as StudentORM
from app.models.parent_link import ParentStudentLink as LinkORM
from app.contexts.identity.domain.user import User
from app.contexts.identity.domain.repositories import UserRepository, ParentLinkRepository


def _to_domain(row: UserORM) -> User:
    return User(
        id=row.id, name=row.name, email=row.email, hashed_password=row.hashed_password,
        google_sub=row.google_sub, role=row.role, school_id=row.school_id, created_at=row.created_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def get(self, user_id: str) -> User | None:
        row = self.session.get(UserORM, user_id)
        return _to_domain(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self.session.query(UserORM).filter(UserORM.email == email).first()
        return _to_domain(row) if row else None

    def find_by_email_ci(self, email: str) -> User | None:
        row = self.session.query(UserORM).filter(func.lower(UserORM.email) == email.strip().lower()).first()
        return _to_domain(row) if row else None

    def email_exists(self, email: str) -> bool:
        return self.session.query(UserORM.id).filter(UserORM.email == email).first() is not None

    def add(self, user: User) -> None:
        self.session.add(UserORM(
            id=user.id, school_id=user.school_id, name=user.name, email=user.email,
            hashed_password=user.hashed_password, google_sub=user.google_sub, role=user.role,
        ))

    def save(self, user: User) -> None:
        row = self.session.get(UserORM, user.id)
        if row is None:
            return
        row.google_sub = user.google_sub


class SqlAlchemyParentLinkRepository(ParentLinkRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def student_ids_for_guardian_email(self, email: str) -> list[str]:
        rows = (
            self.session.query(StudentORM.id)
            .filter(func.lower(StudentORM.guardian_email) == email.strip().lower())
            .all()
        )
        return [r[0] for r in rows]

    def linked_student_ids(self, parent_id: str) -> set[str]:
        rows = self.session.query(LinkORM.student_id).filter(LinkORM.parent_id == parent_id).all()
        return {r[0] for r in rows}

    def add_link(self, link_id: str, parent_id: str, student_id: str) -> None:
        self.session.add(LinkORM(id=link_id, parent_id=parent_id, student_id=student_id))
