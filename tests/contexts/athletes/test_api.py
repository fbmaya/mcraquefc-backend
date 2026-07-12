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


def test_patch_student_persists_changes(client, db_session):
    """Regressão: UpdateStudent.execute mutava um objeto de domínio desanexado
    (retornado por `get`, que já é `_to_domain(row)`) sem chamar `students.add`
    antes do commit — a resposta do PATCH vinha certa, mas nada era persistido.
    Este teste relê via uma requisição GET separada (nova leitura no banco)
    para confirmar que a mudança realmente foi salva."""
    _seed_manager(db_session)
    h = _token(client)
    created = client.post(
        "/students/", headers=h,
        json={"name": "Lucas", "guardian_email": "pai@t.com", "position": "Zagueiro"},
    )
    assert created.status_code == 201, created.text
    student_id = created.json()["id"]

    patched = client.patch(
        "/students/" + student_id, headers=h,
        json={"position": "Atacante", "guardian_email": "novo@t.com"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["position"] == "Atacante"
    assert patched.json()["guardian_email"] == "novo@t.com"

    reread = client.get("/students/" + student_id, headers=h)
    assert reread.status_code == 200, reread.text
    assert reread.json()["position"] == "Atacante"
    assert reread.json()["guardian_email"] == "novo@t.com"


def test_delete_student(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    created = client.post("/students/", headers=h, json={"name": "Lucas", "guardian_email": "pai@t.com"})
    assert created.status_code == 201, created.text
    student_id = created.json()["id"]

    deleted = client.delete("/students/" + student_id, headers=h)
    assert deleted.status_code == 204

    reread = client.get("/students/" + student_id, headers=h)
    assert reread.status_code == 404


def test_get_student_nonexistent_id_returns_404(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    r = client.get("/students/" + str(uuid.uuid4()), headers=h)
    assert r.status_code == 404


def test_set_student_active_toggle(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    created = client.post("/students/", headers=h, json={"name": "Lucas", "guardian_email": "pai@t.com"})
    sid = created.json()["id"]
    assert created.json()["active"] is True
    off = client.patch(f"/students/{sid}/active", headers=h, json={"active": False})
    assert off.status_code == 200 and off.json()["active"] is False
    # persistiu
    assert client.get(f"/students/{sid}", headers=h).json()["active"] is False
    on = client.patch(f"/students/{sid}/active", headers=h, json={"active": True})
    assert on.json()["active"] is True


def test_set_student_active_missing_404(client, db_session):
    _seed_manager(db_session)
    h = _token(client)
    assert client.patch(f"/students/{uuid.uuid4()}/active", headers=h, json={"active": False}).status_code == 404


def test_parent_students_reconciles_by_guardian_email(client, db_session):
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password

    school = _seed_manager(db_session)
    manager_headers = _token(client)

    created = client.post(
        "/students/", headers=manager_headers,
        json={"name": "Filho", "guardian_email": "mae@t.com"},
    )
    assert created.status_code == 201, created.text

    db_session.add(User(
        id=str(uuid.uuid4()), school_id=None, name="Mãe", email="mae@t.com",
        hashed_password=hash_password("y"), role=UserRole.parent,
    ))
    db_session.commit()

    parent_headers = _token(client, email="mae@t.com", pw="y")
    r = client.get("/parent/students", headers=parent_headers)
    assert r.status_code == 200, r.text
    assert [s["name"] for s in r.json()] == ["Filho"]
