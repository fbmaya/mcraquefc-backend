from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from app.contexts.performance.infrastructure.repositories import SqlAlchemyMatchRepository


def match_repo(db: Session = Depends(get_db)) -> SqlAlchemyMatchRepository:
    return SqlAlchemyMatchRepository(db)


def uow(db: Session = Depends(get_db)) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db)
