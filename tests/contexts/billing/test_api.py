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
                hashed_password=hash_password("x"), role=UserRole.manager))
    sid = str(uuid.uuid4())
    db.add(Student(id=sid, school_id=s.id, name="Lucas", guardian_email="p@t.com"))
    db.commit()
    return sid


def _token(client):
    r = client.post("/auth/token", data={"username": "g@t.com", "password": "x"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_list_and_filter(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    r = client.post("/payments/", headers=h, json={
        "student_id": sid, "month_key": "2026-06", "amount": 150.0, "status": "paid"})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "paid" and r.json()["amount"] == 150.0
    lst = client.get("/payments/", headers=h)
    assert [p["month_key"] for p in lst.json()] == ["2026-06"]
    assert client.get("/payments/?month_key=2026-06", headers=h).json()[0]["student_id"] == sid


def test_create_unknown_student_404(client, db_session):
    _seed(db_session)
    h = _token(client)
    r = client.post("/payments/", headers=h, json={"student_id": "ghost", "month_key": "2026-06"})
    assert r.status_code == 404


def test_create_duplicate_month_409(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    body = {"student_id": sid, "month_key": "2026-06", "amount": 100.0}
    assert client.post("/payments/", headers=h, json=body).status_code == 201
    assert client.post("/payments/", headers=h, json=body).status_code == 409


def test_update_persists(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    pid = client.post("/payments/", headers=h, json={"student_id": sid, "month_key": "2026-06"}).json()["id"]
    up = client.patch(f"/payments/{pid}", headers=h, json={"amount": 200.0, "status": "paid"})
    assert up.status_code == 200 and up.json()["amount"] == 200.0 and up.json()["status"] == "paid"
    assert client.get("/payments/", headers=h).json()[0]["amount"] == 200.0


def test_delete_and_missing(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    pid = client.post("/payments/", headers=h, json={"student_id": sid, "month_key": "2026-06"}).json()["id"]
    assert client.delete(f"/payments/{pid}", headers=h).status_code == 204
    assert client.get("/payments/", headers=h).json() == []
    assert client.patch("/payments/nope", headers=h, json={"amount": 1.0}).status_code == 404


def test_requires_manager_role(client, db_session):
    # coach must not access payments (manager-exclusive)
    sid = _seed(db_session)
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    from app.models.student import Student
    school_id = db_session.get(Student, sid).school_id
    db_session.add(User(id=str(uuid.uuid4()), school_id=school_id, name="C", email="c@t.com",
                        hashed_password=hash_password("x"), role=UserRole.coach))
    db_session.commit()
    r = client.post("/auth/token", data={"username": "c@t.com", "password": "x"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/payments/", headers=h).status_code == 403
