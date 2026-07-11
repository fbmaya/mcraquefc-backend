import uuid
from app.database import SessionLocal
from app.models.license import PlanType, LicenseStatus, License as LicenseORM
from app.models.user import User as UserORM, UserRole
from app.models.student import Student as StudentORM
from app.contexts.platform.domain.tenant import School
from app.contexts.platform.infrastructure.repositories import SqlAlchemyPlatformRepository


def _repo(db):
    return SqlAlchemyPlatformRepository(db)


def test_add_school_persists_school_and_license(db_session):
    repo = _repo(db_session)
    s = School.open(id=repo.next_id(), name="Escola X", license_id=repo.next_id())
    repo.add_school(s)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = _repo(fresh).get_school(s.id)
        assert got is not None and got.name == "Escola X" and got.active is True
        assert got.license.plan == PlanType.trial and got.license.max_students == 30
        # Family: default não incluso, sem preço
        assert got.license.family_included is False
        assert got.license.family_price_per_student is None
    finally:
        fresh.close()


def test_license_family_fields_roundtrip(db_session):
    repo = _repo(db_session)
    s = School.open(id=repo.next_id(), name="X", license_id=repo.next_id())
    repo.add_school(s)
    db_session.commit()
    # ativa Family incluso direto no ORM (a edição via caso de uso vem na Fatia D)
    row = db_session.query(LicenseORM).filter(LicenseORM.school_id == s.id).one()
    row.family_included = True
    row.family_price_per_student = 15.0
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = _repo(fresh).get_school(s.id)
        assert got.license.family_included is True
        assert got.license.family_price_per_student == 15.0
    finally:
        fresh.close()


def test_save_school_updates_and_upserts_license(db_session):
    repo = _repo(db_session)
    s = School.open(id=repo.next_id(), name="X", license_id=repo.next_id())
    repo.add_school(s)
    db_session.commit()
    s.change_details(name="Novo Nome")
    s.apply_license(license_id=repo.next_id(), status=LicenseStatus.suspended, max_coaches=9)
    repo.save_school(s)
    db_session.commit()
    fresh = SessionLocal()
    try:
        got = _repo(fresh).get_school(s.id)
        assert got.name == "Novo Nome" and got.active is False
        assert got.license.status == LicenseStatus.suspended and got.license.max_coaches == 9
        # não deve duplicar licença (school_id é unique)
        assert fresh.query(LicenseORM).filter(LicenseORM.school_id == s.id).count() == 1
    finally:
        fresh.close()


def test_save_school_creates_license_when_missing(db_session):
    repo = _repo(db_session)
    s = School.open(id=repo.next_id(), name="X", license_id=repo.next_id())
    s.license = None  # escola grandfathered sem licença
    repo.add_school(s)
    db_session.commit()
    s.apply_license(license_id=repo.next_id(), plan=PlanType.pro)
    repo.save_school(s)
    db_session.commit()
    got = repo.get_school(s.id)
    assert got.license is not None and got.license.plan == PlanType.pro


def _seed_staff(db, repo, school_id):
    db.add(UserORM(id=repo.next_id(), school_id=school_id, name="Ger", email="g@t.com",
                   hashed_password="h", role=UserRole.manager))
    db.add(UserORM(id=repo.next_id(), school_id=school_id, name="Prof", email="c@t.com",
                   hashed_password="h", role=UserRole.coach))
    db.add(StudentORM(id=repo.next_id(), school_id=school_id, name="Aluno", guardian_email="p@t.com"))
    db.commit()


def test_counts_and_overview_and_staff(db_session):
    repo = _repo(db_session)
    s = School.open(id=repo.next_id(), name="X", license_id=repo.next_id())
    repo.add_school(s)
    db_session.commit()
    _seed_staff(db_session, repo, s.id)

    assert repo.school_counts(s.id) == (1, 1, 1)
    assert repo.coach_count(s.id) == 1
    assert repo.email_exists("g@t.com") is True and repo.email_exists("nope@t.com") is False
    assert {m.email for m in repo.list_staff(s.id)} == {"g@t.com", "c@t.com"}

    ov = repo.platform_overview()
    assert ov["total_schools"] == 1 and ov["active_schools"] == 1
    assert ov["total_students"] == 1 and ov["total_users"] == 2  # exclui platform_admin
    assert ov["licenses_by_plan"].get(PlanType.trial) == 1


def test_add_and_remove_staff(db_session):
    repo = _repo(db_session)
    s = School.open(id=repo.next_id(), name="X", license_id=repo.next_id())
    repo.add_school(s)
    db_session.commit()
    m = repo.add_staff(id=repo.next_id(), school_id=s.id, name="A", email="a@t.com",
                       hashed_password="h", role=UserRole.manager)
    db_session.commit()
    assert repo.get_staff(m.id).email == "a@t.com"
    repo.remove_staff(m.id)
    db_session.commit()
    assert repo.get_staff(m.id) is None
