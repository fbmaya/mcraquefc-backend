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


def test_register_parent_returns_token_and_me(client, db_session):
    r = client.post("/auth/register", json={"name": "Mãe", "email": "mae@t.com", "password": "s3nha"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "parent" and body["school_id"] is None
    h = {"Authorization": f"Bearer {body['access_token']}"}
    me = client.get("/auth/me", headers=h)
    assert me.status_code == 200 and me.json()["email"] == "mae@t.com"


def test_register_duplicate_email_400(client, db_session):
    body = {"name": "A", "email": "a@t.com", "password": "s"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 400


def test_register_non_parent_role_403(client, db_session):
    r = client.post("/auth/register",
                    json={"name": "Chefe", "email": "c@t.com", "password": "s", "role": "manager"})
    assert r.status_code == 403


def test_login_success_and_wrong_password(client, db_session):
    client.post("/auth/register", json={"name": "A", "email": "a@t.com", "password": "secret"})
    ok = client.post("/auth/token", data={"username": "a@t.com", "password": "secret"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/auth/token", data={"username": "a@t.com", "password": "nope"})
    assert bad.status_code == 401


def test_register_reconciles_parent_links(client, db_session):
    # gestor cria aluno com guardian_email; ao registrar, o responsável é vinculado
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db_session.add(school)
    db_session.add(User(id=str(uuid.uuid4()), school_id=school.id, name="G", email="m@t.com",
                        hashed_password=hash_password("x"), role=UserRole.manager))
    db_session.commit()
    mgr = client.post("/auth/token", data={"username": "m@t.com", "password": "x"})
    mh = {"Authorization": f"Bearer {mgr.json()['access_token']}"}
    created = client.post("/students/", headers=mh, json={"name": "Filho", "guardian_email": "mae@t.com"})
    assert created.status_code == 201, created.text

    reg = client.post("/auth/register", json={"name": "Mãe", "email": "mae@t.com", "password": "s"})
    ph = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    kids = client.get("/parent/students", headers=ph)
    assert kids.status_code == 200 and [s["name"] for s in kids.json()] == ["Filho"]


def test_google_login_unconfigured_returns_503(client, db_session):
    # em teste, google_client_id não está setado
    r = client.post("/auth/google", json={"credential": "whatever"})
    assert r.status_code == 503
