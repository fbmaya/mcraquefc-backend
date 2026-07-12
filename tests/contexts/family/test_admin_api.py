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
    """platform_admin + escola + um responsável. Retorna (school_id, parent_email)."""
    from app.auth.jwt import hash_password
    from app.models.school import School
    from app.models.user import User, UserRole
    db.add(User(id=str(uuid.uuid4()), school_id=None, name="Admin", email="admin@mcfc.com",
                hashed_password=hash_password("x"), role=UserRole.platform_admin))
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    parent = User(id=str(uuid.uuid4()), school_id=None, name="Mãe", email="mae@t.com",
                  hashed_password=hash_password("y"), role=UserRole.parent)
    db.add(parent)
    db.commit()
    return school.id, "mae@t.com"


def _token(client, email="admin@mcfc.com", pw="x"):
    r = client.post("/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_list_cancel_subscription(client, db_session):
    school_id, parent_email = _seed(db_session)
    h = _token(client)
    r = client.post(f"/platform/schools/{school_id}/family-subscriptions", headers=h,
                    json={"parent_email": parent_email, "price_tier": "promo"})
    assert r.status_code == 201, r.text
    sub_id = r.json()["id"]
    assert r.json()["status"] == "active" and r.json()["price_tier"] == "promo"
    assert r.json()["parent_email"] == parent_email  # resposta enriquecida
    # lista
    lst = client.get(f"/platform/schools/{school_id}/family-subscriptions", headers=h)
    assert [s["id"] for s in lst.json()] == [sub_id]
    assert lst.json()[0]["parent_email"] == parent_email
    # duplicado → 409 (e-mail case-insensitive)
    dup = client.post(f"/platform/schools/{school_id}/family-subscriptions", headers=h,
                      json={"parent_email": parent_email.upper()})
    assert dup.status_code == 409
    # cancela
    canc = client.delete(f"/platform/family-subscriptions/{sub_id}", headers=h)
    assert canc.status_code == 200 and canc.json()["status"] == "cancelled"


def test_create_unknown_parent_or_school_404(client, db_session):
    school_id, parent_email = _seed(db_session)
    h = _token(client)
    assert client.post(f"/platform/schools/{school_id}/family-subscriptions", headers=h,
                       json={"parent_email": "ghost@t.com"}).status_code == 404
    assert client.post("/platform/schools/ghost/family-subscriptions", headers=h,
                       json={"parent_email": parent_email}).status_code == 404


def test_cancel_missing_404(client, db_session):
    _seed(db_session)
    h = _token(client)
    assert client.delete("/platform/family-subscriptions/nope", headers=h).status_code == 404


def test_requires_platform_admin(client, db_session):
    school_id, parent_id = _seed(db_session)
    from app.models.school import School
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    s2 = School(id=str(uuid.uuid4()), name="E2", primary_color="#000")
    db_session.add(s2)
    db_session.add(User(id=str(uuid.uuid4()), school_id=s2.id, name="G", email="g@t.com",
                        hashed_password=hash_password("x"), role=UserRole.manager))
    db_session.commit()
    h = _token(client, "g@t.com", "x")
    assert client.get(f"/platform/schools/{school_id}/family-subscriptions", headers=h).status_code == 403
