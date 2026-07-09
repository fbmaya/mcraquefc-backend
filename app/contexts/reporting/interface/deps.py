from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.contexts.reporting.infrastructure.repositories import SqlAlchemyReportingRepository


def reporting_repo(db: Session = Depends(get_db)) -> SqlAlchemyReportingRepository:
    return SqlAlchemyReportingRepository(db)
