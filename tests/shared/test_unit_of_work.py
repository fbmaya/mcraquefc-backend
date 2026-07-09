from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_commit_delegates_to_session():
    s = FakeSession()
    SqlAlchemyUnitOfWork(s).commit()
    assert s.committed is True


def test_rollback_delegates_to_session():
    s = FakeSession()
    SqlAlchemyUnitOfWork(s).rollback()
    assert s.rolled_back is True


def test_unit_of_work_protocol_module_is_infra_free():
    """A porta pura (unit_of_work.py) não pode importar sqlalchemy — assim a
    camada de aplicação depende só da porta, sem puxar o ORM (regra de dependência)."""
    import ast
    from pathlib import Path

    src = Path("app/shared/infrastructure/unit_of_work.py").read_text()
    modules: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            modules.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert not any("sqlalchemy" in m for m in modules), modules
