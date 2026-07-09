from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from app.contexts.billing.infrastructure.repositories import SqlAlchemyPaymentRepository


def payment_repo(db: Session = Depends(get_db)) -> SqlAlchemyPaymentRepository:
    return SqlAlchemyPaymentRepository(db)


def uow(db: Session = Depends(get_db)) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db)
