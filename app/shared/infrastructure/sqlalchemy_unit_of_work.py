from sqlalchemy.orm import Session


class SqlAlchemyUnitOfWork:
    """UoW fina sobre a Session request-scoped do FastAPI (Depends(get_db))."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
