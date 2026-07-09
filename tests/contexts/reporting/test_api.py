import datetime as dt
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
    from app.auth.jwt import hash_password
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.models.student import Student
    from app.models.match import Match, MatchStat
    s = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(s)
    db.add(User(id=str(uuid.uuid4()), school_id=s.id, name="G", email="g@t.com",
                hashed_password=hash_password("x"), role=UserRole.coach))
    sid = str(uuid.uuid4())
    db.add(Student(id=sid, school_id=s.id, name="Lucas", position="ATA", guardian_email="p@t.com"))
    m = Match(id=str(uuid.uuid4()), school_id=s.id, date=dt.date(2026, 6, 1), opponent="Rival")
    db.add(m)
    db.add(MatchStat(id=str(uuid.uuid4()), match_id=m.id, student_id=sid, goals=3, assists=1, played=True))
    db.commit()
    return sid


def _token(client, email="g@t.com", pw="x"):
    r = client.post("/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_overview_and_leaderboard(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    ov = client.get("/stats/overview", headers=h)
    assert ov.status_code == 200, ov.text
    assert ov.json()["total_students"] == 1
    assert ov.json()["top_scorers"][0]["student_id"] == sid
    lb = client.get("/stats/leaderboard?limit=5", headers=h)
    assert lb.status_code == 200 and lb.json()["top_scorers"][0]["goals"] == 3


def test_student_stats_and_peers(client, db_session):
    sid = _seed(db_session)
    h = _token(client)
    r = client.get(f"/stats/students/{sid}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Lucas" and r.json()["matches"]["goals"] == 3
    peers = client.get(f"/stats/students/{sid}/peers", headers=h)
    assert peers.status_code == 200 and "class_avg" in peers.json()


def test_student_stats_unknown_404(client, db_session):
    _seed(db_session)
    h = _token(client)
    assert client.get("/stats/students/ghost", headers=h).status_code == 404


def test_parent_summary_uses_reporting(client, db_session):
    """O /parent/.../summary (router antigo) agora compõe via contexto Reporting."""
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db_session.add(school)
    db_session.add(User(id=str(uuid.uuid4()), school_id=school.id, name="Gestor", email="m@t.com",
                        hashed_password=hash_password("x"), role=UserRole.manager))
    db_session.commit()
    mgr = _token(client, "m@t.com", "x")
    created = client.post("/students/", headers=mgr,
                          json={"name": "Filho", "guardian_email": "mae@t.com"})
    assert created.status_code == 201, created.text
    db_session.add(User(id=str(uuid.uuid4()), school_id=None, name="Mãe", email="mae@t.com",
                        hashed_password=hash_password("y"), role=UserRole.parent))
    db_session.commit()
    parent = _token(client, "mae@t.com", "y")
    sid = client.get("/parent/students", headers=parent).json()[0]["id"]
    r = client.get(f"/parent/students/{sid}/summary", headers=parent)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Filho"
    assert "radar" in body and "peers" in body and "class_avg" in body["peers"]
