from app.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


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
