from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from app.contexts.identity.infrastructure.repositories import (
    SqlAlchemyUserRepository, SqlAlchemyParentLinkRepository,
)


def user_repo(db: Session = Depends(get_db)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db)


def link_repo(db: Session = Depends(get_db)) -> SqlAlchemyParentLinkRepository:
    return SqlAlchemyParentLinkRepository(db)


def uow(db: Session = Depends(get_db)) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db)
