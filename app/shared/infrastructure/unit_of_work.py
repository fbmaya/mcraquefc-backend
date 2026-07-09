from typing import Protocol


class UnitOfWork(Protocol):
    """Porta pura (sem infra). A camada de aplicação depende só disto;
    a implementação concreta vive em sqlalchemy_unit_of_work.py."""

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
