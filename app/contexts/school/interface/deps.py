from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from app.contexts.school.infrastructure.repositories import (
    SqlAlchemyClassRepository, SqlAlchemyEnrollmentRepository, SqlAlchemyStudentLookup,
)


def class_repo(db: Session = Depends(get_db)) -> SqlAlchemyClassRepository:
    return SqlAlchemyClassRepository(db)


def enrollment_repo(db: Session = Depends(get_db)) -> SqlAlchemyEnrollmentRepository:
    return SqlAlchemyEnrollmentRepository(db)


def student_lookup(db: Session = Depends(get_db)) -> SqlAlchemyStudentLookup:
    return SqlAlchemyStudentLookup(db)


def uow(db: Session = Depends(get_db)) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db)
