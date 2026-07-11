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


def _admin(db):
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    db.add(User(id=str(uuid.uuid4()), school_id=None, name="Admin", email="admin@mcfc.com",
                hashed_password=hash_password("x"), role=UserRole.platform_admin))
    db.commit()


def _token(client, email="admin@mcfc.com", pw="x"):
    r = client.post("/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_school_starts_trial_and_detail(client, db_session):
    _admin(db_session)
    h = _token(client)
    r = client.post("/platform/schools", headers=h, json={"name": "Escola X"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert r.json()["active"] is True
    lst = client.get("/platform/schools", headers=h)
    assert [s["name"] for s in lst.json()] == ["Escola X"]
    detail = client.get(f"/platform/schools/{sid}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["license"]["plan"] == "trial"
    assert detail.json()["student_count"] == 0


def test_update_school_and_license_syncs_active(client, db_session):
    _admin(db_session)
    h = _token(client)
    sid = client.post("/platform/schools", headers=h, json={"name": "X"}).json()["id"]
    up = client.patch(f"/platform/schools/{sid}", headers=h, json={"name": "Novo"})
    assert up.status_code == 200 and up.json()["name"] == "Novo"
    lic = client.patch(f"/platform/schools/{sid}/license", headers=h,
                       json={"status": "suspended", "max_coaches": 5})
    assert lic.status_code == 200 and lic.json()["status"] == "suspended" and lic.json()["max_coaches"] == 5
    # school.active sincronizado com o status da licença
    assert client.get(f"/platform/schools/{sid}", headers=h).json()["school"]["active"] is False


def test_update_missing_school_404(client, db_session):
    _admin(db_session)
    h = _token(client)
    assert client.patch("/platform/schools/nope", headers=h, json={"name": "X"}).status_code == 404


def test_license_family_fields_and_over_quota_alert(client, db_session):
    import uuid
    from app.models.student import Student
    _admin(db_session)
    h = _token(client)
    sid = client.post("/platform/schools", headers=h, json={"name": "X"}).json()["id"]
    # ativa Family incluso com cota de 1
    lic = client.patch(f"/platform/schools/{sid}/license", headers=h,
                       json={"family_included": True, "family_price_per_student": 15.0, "family_seats": 1})
    assert lic.status_code == 200
    assert lic.json()["family_included"] is True and lic.json()["family_seats"] == 1
    # 1 aluno ativo → dentro da cota, sem alerta
    db_session.add(Student(id=str(uuid.uuid4()), school_id=sid, name="A", guardian_email="a@t.com", active=True))
    db_session.commit()
    d = client.get(f"/platform/schools/{sid}", headers=h).json()
    assert d["active_student_count"] == 1 and d["family_over_quota"] is False
    # 2º aluno ativo → passou da cota → alerta (mas não bloqueia nada)
    db_session.add(Student(id=str(uuid.uuid4()), school_id=sid, name="B", guardian_email="b@t.com", active=True))
    db_session.commit()
    d2 = client.get(f"/platform/schools/{sid}", headers=h).json()
    assert d2["active_student_count"] == 2 and d2["family_over_quota"] is True


def test_staff_create_list_delete(client, db_session):
    _admin(db_session)
    h = _token(client)
    sid = client.post("/platform/schools", headers=h, json={"name": "X"}).json()["id"]
    r = client.post(f"/platform/schools/{sid}/users", headers=h,
                    json={"name": "Ger", "email": "ger@t.com", "password": "s", "role": "manager"})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    assert r.json()["role"] == "manager"
    assert [u["email"] for u in client.get(f"/platform/schools/{sid}/users", headers=h).json()] == ["ger@t.com"]
    # email duplicado -> 400
    dup = client.post(f"/platform/schools/{sid}/users", headers=h,
                      json={"name": "Outro", "email": "ger@t.com", "password": "s", "role": "coach"})
    assert dup.status_code == 400
    assert client.delete(f"/platform/schools/{sid}/users/{uid}", headers=h).status_code == 204
    assert client.delete(f"/platform/schools/{sid}/users/nope", headers=h).status_code == 404


def test_coach_limit_enforced(client, db_session):
    _admin(db_session)
    h = _token(client)
    sid = client.post("/platform/schools", headers=h, json={"name": "X"}).json()["id"]  # trial: max_coaches=2
    for i in range(2):
        ok = client.post(f"/platform/schools/{sid}/users", headers=h,
                         json={"name": f"C{i}", "email": f"c{i}@t.com", "password": "s", "role": "coach"})
        assert ok.status_code == 201, ok.text
    third = client.post(f"/platform/schools/{sid}/users", headers=h,
                        json={"name": "C3", "email": "c3@t.com", "password": "s", "role": "coach"})
    assert third.status_code == 403
    assert "Limite de professores" in third.json()["detail"]


def test_overview(client, db_session):
    _admin(db_session)
    h = _token(client)
    client.post("/platform/schools", headers=h, json={"name": "A"})
    client.post("/platform/schools", headers=h, json={"name": "B"})
    ov = client.get("/platform/overview", headers=h)
    assert ov.status_code == 200
    assert ov.json()["total_schools"] == 2 and ov.json()["active_schools"] == 2
    assert ov.json()["licenses_by_plan"]["trial"] == 2


def test_requires_platform_admin(client, db_session):
    # manager must not reach platform endpoints
    _admin(db_session)
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db_session.add(school)
    db_session.add(User(id=str(uuid.uuid4()), school_id=school.id, name="G", email="m@t.com",
                        hashed_password=hash_password("x"), role=UserRole.manager))
    db_session.commit()
    h = _token(client, "m@t.com", "x")
    assert client.get("/platform/schools", headers=h).status_code == 403
