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


def _seed_manager(db):
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    s = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(s)
    db.add(User(id=str(uuid.uuid4()), school_id=s.id, name="G", email="g@t.com",
                hashed_password=hash_password("x"), role=UserRole.manager))
    db.commit()
    return s.id


def _seed_student(db, school_id):
    from app.models.student import Student
    sid = str(uuid.uuid4())
    db.add(Student(id=sid, school_id=school_id, name="Lucas", guardian_email="p@t.com"))
    db.commit()
    return sid


def _token(client, email="g@t.com", pw="x"):
    r = client.post("/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_list_and_update_class(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    r = client.post("/classes/", headers=h, json={"name": "Sub-9 A", "period": "Manhã"})
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert r.json()["period"] == "Manhã"
    assert r.json()["student_ids"] == []
    # update persists (re-read via GET list)
    up = client.patch(f"/classes/{cid}", headers=h, json={"period": "Noite"})
    assert up.status_code == 200 and up.json()["period"] == "Noite"
    lst = client.get("/classes/", headers=h)
    assert lst.json()[0]["period"] == "Noite"


def test_invalid_period_rejected(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    r = client.post("/classes/", headers=h, json={"name": "X", "period": "Madrugada"})
    assert r.status_code == 422


def test_enroll_and_unenroll_flow(client, db_session):
    school_id = _seed_manager(db_session)
    stu = _seed_student(db_session, school_id)
    h = _token(client)
    cid = client.post("/classes/", headers=h, json={"name": "A"}).json()["id"]
    en = client.post(f"/classes/{cid}/enroll", headers=h, json={"student_id": stu})
    assert en.status_code == 201 and en.json()["active"] is True
    # reflected in the class view
    assert client.get("/classes/", headers=h).json()[0]["student_ids"] == [stu]
    # unenroll
    assert client.delete(f"/classes/{cid}/enroll/{stu}", headers=h).status_code == 204
    assert client.get("/classes/", headers=h).json()[0]["student_ids"] == []


def test_enroll_rejects_student_from_other_school(client, db_session):
    school_id = _seed_manager(db_session)
    h = _token(client)
    cid = client.post("/classes/", headers=h, json={"name": "A"}).json()["id"]
    r = client.post(f"/classes/{cid}/enroll", headers=h, json={"student_id": "nonexistent"})
    assert r.status_code == 404
