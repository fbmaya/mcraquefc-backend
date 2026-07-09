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


def test_create_match_with_stats_and_list(client, db_session):
    stu = _seed_manager(db_session)
    h = _token(client)
    r = client.post("/matches/", headers=h, json={
        "date": "2026-06-10", "opponent": "Rival FC", "score_us": 4, "score_them": 1,
        "stats": [{"student_id": stu, "goals": 2, "assists": 1}]})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["opponent"] == "Rival FC"
    assert len(body["stats"]) == 1 and body["stats"][0]["goals"] == 2
    lst = client.get("/matches/", headers=h)
    assert [m["opponent"] for m in lst.json()] == ["Rival FC"]


def test_update_match_persists(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    mid = client.post("/matches/", headers=h, json={"date": "2026-06-10", "opponent": "A"}).json()["id"]
    up = client.patch(f"/matches/{mid}", headers=h, json={"opponent": "Novo FC", "score_us": 3})
    assert up.status_code == 200 and up.json()["opponent"] == "Novo FC" and up.json()["score_us"] == 3
    assert client.get("/matches/", headers=h).json()[0]["opponent"] == "Novo FC"


def test_delete_match(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    mid = client.post("/matches/", headers=h, json={"date": "2026-06-10", "opponent": "A"}).json()["id"]
    assert client.delete(f"/matches/{mid}", headers=h).status_code == 204
    assert client.get("/matches/", headers=h).json() == []


def test_update_missing_match_404(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    assert client.patch("/matches/nope", headers=h, json={"opponent": "X"}).status_code == 404
