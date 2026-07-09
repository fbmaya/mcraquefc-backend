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
    from app.models.class_ import Class
    from app.models.student import Student
    from app.auth.jwt import hash_password
    s = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(s)
    db.add(User(id=str(uuid.uuid4()), school_id=s.id, name="G", email="g@t.com",
                hashed_password=hash_password("x"), role=UserRole.manager))
    cid = str(uuid.uuid4())
    db.add(Class(id=cid, school_id=s.id, name="Sub-9"))
    sid = str(uuid.uuid4())
    db.add(Student(id=sid, school_id=s.id, name="Lucas", guardian_email="p@t.com"))
    db.commit()
    return cid, sid


def _token(client):
    r = client.post("/auth/token", data={"username": "g@t.com", "password": "x"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_session_with_records_and_list(client, db_session):
    cid, sid = _seed(db_session)
    h = _token(client)
    r = client.post("/attendance/", headers=h, json={
        "class_id": cid, "date": "2026-06-10", "notes": "treino",
        "records": [{"student_id": sid, "present": True}]})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["class_id"] == cid
    assert len(body["records"]) == 1 and body["records"][0]["present"] is True
    lst = client.get("/attendance/", headers=h)
    assert [s["class_id"] for s in lst.json()] == [cid]
    scoped = client.get(f"/attendance/?class_id={cid}", headers=h)
    assert len(scoped.json()) == 1


def test_create_session_unknown_class_404(client, db_session):
    _seed(db_session)
    h = _token(client)
    r = client.post("/attendance/", headers=h, json={
        "class_id": "nope", "date": "2026-06-10", "records": []})
    assert r.status_code == 404


def test_create_session_foreign_student_400(client, db_session):
    cid, _ = _seed(db_session)
    h = _token(client)
    r = client.post("/attendance/", headers=h, json={
        "class_id": cid, "date": "2026-06-10",
        "records": [{"student_id": "ghost", "present": True}]})
    assert r.status_code == 400


def test_delete_session(client, db_session):
    cid, sid = _seed(db_session)
    h = _token(client)
    sess_id = client.post("/attendance/", headers=h, json={
        "class_id": cid, "date": "2026-06-10", "records": []}).json()["id"]
    assert client.delete(f"/attendance/{sess_id}", headers=h).status_code == 204
    assert client.get("/attendance/", headers=h).json() == []


def test_delete_missing_session_404(client, db_session):
    _seed(db_session)
    h = _token(client)
    assert client.delete("/attendance/nope", headers=h).status_code == 404
