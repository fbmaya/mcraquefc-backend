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


def _seed(db):
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.models.student import Student
    from app.auth.jwt import hash_password
    s = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(s)
    db.add(User(id=str(uuid.uuid4()), school_id=s.id, name="G", email="g@t.com",
                hashed_password=hash_password("x"), role=UserRole.coach))
    sid = str(uuid.uuid4())
    db.add(Student(id=sid, school_id=s.id, name="Lucas", guardian_email="p@t.com"))
    db.commit()
    return sid


def _token(client):
    r = client.post("/auth/token", data={"username": "g@t.com", "password": "x"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_evaluation_computes_axes_and_lists(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    r = client.post("/evaluations/", headers=h, json={
        "student_id": sid, "date": "2026-06-10",
        "passing": 8, "finishing": 6, "dribbling": 7})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["passing"] == 8 and body["technique"] == 7.0
    assert body["evaluated_by"] is not None  # set from current user
    lst = client.get("/evaluations/", headers=h)
    assert [e["student_id"] for e in lst.json()] == [sid]
    assert client.get(f"/evaluations/?student_id={sid}", headers=h).json()[0]["technique"] == 7.0


def test_create_unknown_student_404(client, db_session):
    _seed(db_session)
    h = _token(client)
    r = client.post("/evaluations/", headers=h, json={"student_id": "ghost", "date": "2026-06-10"})
    assert r.status_code == 404


def test_create_rejects_out_of_range_skill(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    r = client.post("/evaluations/", headers=h, json={"student_id": sid, "date": "2026-06-10", "passing": 42})
    assert r.status_code == 422  # schema enforces 0-10


def test_delete_and_missing(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    eid = client.post("/evaluations/", headers=h, json={"student_id": sid, "date": "2026-06-10"}).json()["id"]
    assert client.delete(f"/evaluations/{eid}", headers=h).status_code == 204
    assert client.get("/evaluations/", headers=h).json() == []
    assert client.delete("/evaluations/nope", headers=h).status_code == 404
