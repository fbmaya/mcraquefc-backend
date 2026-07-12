"""Portal do responsável (/parent/*): compõe leituras de vários contextos,
guardado pelo vínculo pai↔aluno. Vive no contexto Athletes (dono da relação)."""
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


def _token(client, email, pw):
    r = client.post("/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _seed(db, family_included=True):
    """Escola + gestor + aluno (guardian mae@t.com) com dados nos 4 contextos + responsável vinculado.
    Cria licença com family_included (default True) p/ liberar o portal premium via Caminho 1."""
    from app.auth.jwt import hash_password
    from app.models.school import School
    from app.models.license import License
    from app.models.user import User, UserRole
    from app.models.student import Student
    from app.models.class_ import Class
    from app.models.payment import Payment, PaymentStatus
    from app.models.evaluation import Evaluation
    from app.models.attendance import AttendanceSession, AttendanceRecord
    from app.models.match import Match, MatchStat
    from app.models.parent_link import ParentStudentLink

    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    # Family incluso por padrão (Caminho 1) → portal premium liberado nos testes felizes.
    db.add(License(id=str(uuid.uuid4()), school_id=school.id, family_included=family_included))
    db.add(User(id=str(uuid.uuid4()), school_id=school.id, name="G", email="g@t.com",
                hashed_password=hash_password("x"), role=UserRole.manager))
    sid = str(uuid.uuid4())
    db.add(Student(id=sid, school_id=school.id, name="Filho", position="ATA", guardian_email="mae@t.com"))
    cls = Class(id=str(uuid.uuid4()), school_id=school.id, name="Sub-9", age_group="U9")
    db.add(cls)

    db.add(Payment(id=str(uuid.uuid4()), student_id=sid, month_key="2026-06",
                   amount=100.0, status=PaymentStatus.paid))
    db.add(Evaluation(id=str(uuid.uuid4()), student_id=sid, date=dt.date(2026, 6, 1),
                      passing=8, finishing=7))
    sess = AttendanceSession(id=str(uuid.uuid4()), class_id=cls.id, date=dt.date(2026, 6, 1))
    db.add(sess)
    db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=sess.id, student_id=sid, present=True))
    m = Match(id=str(uuid.uuid4()), school_id=school.id, date=dt.date(2026, 6, 1), opponent="Rival")
    db.add(m)
    db.add(MatchStat(id=str(uuid.uuid4()), match_id=m.id, student_id=sid, goals=2, played=True))

    parent = User(id=str(uuid.uuid4()), school_id=None, name="Mãe", email="mae@t.com",
                  hashed_password=hash_password("y"), role=UserRole.parent)
    db.add(parent)
    db.add(ParentStudentLink(id=str(uuid.uuid4()), parent_id=parent.id, student_id=sid))
    db.commit()
    return sid, school.id, parent.id


def test_portal_reads_all_contexts(client, db_session):
    sid, _, _ = _seed(db_session)
    h = _token(client, "mae@t.com", "y")

    assert [s["name"] for s in client.get("/parent/students", headers=h).json()] == ["Filho"]

    summary = client.get(f"/parent/students/{sid}/summary", headers=h)
    assert summary.status_code == 200
    assert summary.json()["name"] == "Filho" and "peers" in summary.json()
    assert summary.json()["matches"]["goals"] == 2

    pays = client.get(f"/parent/students/{sid}/payments", headers=h)
    assert pays.status_code == 200 and [p["month_key"] for p in pays.json()] == ["2026-06"]

    evs = client.get(f"/parent/students/{sid}/evaluations", headers=h)
    assert evs.status_code == 200 and evs.json()[0]["passing"] == 8

    att = client.get(f"/parent/students/{sid}/attendance", headers=h)
    assert att.status_code == 200 and len(att.json()) == 1 and att.json()[0]["records"][0]["present"] is True

    matches = client.get(f"/parent/students/{sid}/matches", headers=h)
    assert matches.status_code == 200 and matches.json()[0]["opponent"] == "Rival"


def test_portal_blocks_unlinked_student(client, db_session):
    _seed(db_session)
    # responsável sem vínculo com o aluno alvo
    from app.models.user import User, UserRole
    from app.auth.jwt import hash_password
    db_session.add(User(id=str(uuid.uuid4()), school_id=None, name="Outra", email="outra@t.com",
                        hashed_password=hash_password("z"), role=UserRole.parent))
    db_session.commit()
    h = _token(client, "outra@t.com", "z")
    other_sid = str(uuid.uuid4())
    for path in ("summary", "payments", "evaluations", "attendance", "matches"):
        r = client.get(f"/parent/students/{other_sid}/{path}", headers=h)
        assert r.status_code == 403, f"{path} -> {r.status_code}"


def test_portal_requires_parent_role(client, db_session):
    _seed(db_session)
    h = _token(client, "g@t.com", "x")  # manager
    assert client.get("/parent/students", headers=h).status_code == 403


PREMIUM = ("summary", "evaluations", "attendance", "matches")


def test_premium_blocked_without_family(client, db_session):
    # escola SEM Family incluso e sem assinatura → premium bloqueado; básico livre
    sid, _, _ = _seed(db_session, family_included=False)
    h = _token(client, "mae@t.com", "y")
    for path in PREMIUM:
        r = client.get(f"/parent/students/{sid}/{path}", headers=h)
        assert r.status_code == 402, f"{path} -> {r.status_code}"  # Payment Required
        assert "Family" in r.json()["detail"]
    # livres continuam acessíveis
    assert client.get("/parent/students", headers=h).status_code == 200
    assert client.get(f"/parent/students/{sid}/payments", headers=h).status_code == 200


def test_premium_allowed_via_individual_subscription(client, db_session):
    # sem Family incluso, mas com assinatura individual do responsável → premium liberado
    import uuid as u
    from app.models.family_subscription import FamilySubscription
    sid, school_id, parent_id = _seed(db_session, family_included=False)
    db_session.add(FamilySubscription(id=str(u.uuid4()), parent_id=parent_id, school_id=school_id))
    db_session.commit()
    h = _token(client, "mae@t.com", "y")
    for path in PREMIUM:
        assert client.get(f"/parent/students/{sid}/{path}", headers=h).status_code == 200, path


def test_premium_blocked_when_student_inactive(client, db_session):
    # Family incluso, mas aluno inativo → sem acesso premium (não conta como ativo)
    from app.models.student import Student
    sid, _, _ = _seed(db_session, family_included=True)
    db_session.get(Student, sid).active = False
    db_session.commit()
    h = _token(client, "mae@t.com", "y")
    assert client.get(f"/parent/students/{sid}/summary", headers=h).status_code == 402
