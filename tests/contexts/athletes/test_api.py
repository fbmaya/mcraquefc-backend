import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(db_session):
    from app.main import app
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_manager(db_session):
    import uuid as u
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    s = School(id=str(u.uuid4()), name="E", primary_color="#000")
    db_session.add(s)
    db_session.add(User(id=str(u.uuid4()), school_id=s.id, name="G", email="g@t.com",
                        hashed_password=hash_password("x"), role=UserRole.manager))
    db_session.commit()
    return s


def _token(client, email="g@t.com", pw="x"):
    r = client.post("/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_and_list_student(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    r = client.post("/students/", headers=h, json={"name": "Lucas", "guardian_email": "PAI@t.com"})
    assert r.status_code == 201, r.text
    assert r.json()["guardian_email"] == "pai@t.com"
    assert "access_code" not in r.json()
    lst = client.get("/students/", headers=h)
    assert [s["name"] for s in lst.json()] == ["Lucas"]


def test_create_requires_email(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    r = client.post("/students/", headers=h, json={"name": "SemEmail"})
    assert r.status_code == 422
