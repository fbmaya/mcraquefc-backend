from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from app.contexts.athletes.infrastructure.repositories import (
    SqlAlchemyStudentRepository, SqlAlchemyParentLinkRepository,
)


def student_repo(db: Session = Depends(get_db)) -> SqlAlchemyStudentRepository:
    return SqlAlchemyStudentRepository(db)


def link_repo(db: Session = Depends(get_db)) -> SqlAlchemyParentLinkRepository:
    return SqlAlchemyParentLinkRepository(db)


def uow(db: Session = Depends(get_db)) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db)
