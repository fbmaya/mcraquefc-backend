import pytest
from app.models.license import PlanType, LicenseStatus
from app.models.user import UserRole
from app.contexts.platform.domain.tenant import School
from app.contexts.platform.domain.read_models import StaffMember
from app.contexts.platform.domain.repositories import PlatformRepository
from app.contexts.platform.application import use_cases as uc


class FakePlatform(PlatformRepository):
    def __init__(self):
        self.schools: dict[str, School] = {}
        self.staff: dict[str, StaffMember] = {}
        self.emails: set[str] = set()
        self.counts: dict[str, tuple] = {}      # school_id -> (mgr, coach, student)
        self._n = 0

    def next_id(self):
        self._n += 1
        return f"id{self._n}"

    def add_school(self, school): self.schools[school.id] = school
    def get_school(self, sid): return self.schools.get(sid)
    def list_schools(self): return list(self.schools.values())
    def save_school(self, school): self.schools[school.id] = school

    def school_counts(self, sid): return self.counts.get(sid, (0, 0, 0))
    def coach_count(self, sid): return self.counts.get(sid, (0, 0, 0))[1]
    def platform_overview(self): return {"total_schools": len(self.schools)}

    def list_staff(self, sid): return [m for m in self.staff.values() if m.school_id == sid]
    def get_staff(self, uid): return self.staff.get(uid)
    def email_exists(self, email): return email in self.emails
    def add_staff(self, *, id, school_id, name, email, hashed_password, role):
        m = StaffMember(id=id, name=name, email=email, role=role, school_id=school_id)
        self.staff[id] = m
        self.emails.add(email)
        return m
    def remove_staff(self, uid): self.staff.pop(uid, None)


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


def _school(repo, uow, name="Escola X"):
    return uc.CreateSchool(repo, uow).execute(name=name)


def test_create_school_starts_trial_active():
    repo, uow = FakePlatform(), FakeUoW()
    v = _school(repo, uow)
    assert v.active is True and v.name == "Escola X"
    assert repo.get_school(v.id).license.plan == PlanType.trial
    assert uow.commits == 1


def test_update_school_missing_raises():
    repo = FakePlatform()
    with pytest.raises(uc.SchoolNotFound):
        uc.UpdateSchool(repo, FakeUoW()).execute(school_id="ghost", changes={"name": "X"})


def test_update_license_syncs_active():
    repo, uow = FakePlatform(), FakeUoW()
    v = _school(repo, uow)
    lic = uc.UpdateLicense(repo, FakeUoW()).execute(
        school_id=v.id, changes={"status": LicenseStatus.suspended, "max_coaches": 5})
    assert lic.status == LicenseStatus.suspended and lic.max_coaches == 5
    assert repo.get_school(v.id).active is False


def test_school_detail_includes_counts():
    repo, uow = FakePlatform(), FakeUoW()
    v = _school(repo, uow)
    repo.counts[v.id] = (1, 2, 15)
    detail = uc.GetSchoolDetail(repo).execute(school_id=v.id)
    assert detail.manager_count == 1 and detail.coach_count == 2 and detail.student_count == 15
    assert detail.license.plan == PlanType.trial


def test_create_staff_rejects_duplicate_email():
    repo, uow = FakePlatform(), FakeUoW()
    v = _school(repo, uow)
    uc.CreateStaff(repo, FakeUoW()).execute(school_id=v.id, name="A", email="a@t.com",
                                            hashed_password="h", role=UserRole.manager)
    with pytest.raises(uc.EmailAlreadyUsed):
        uc.CreateStaff(repo, FakeUoW()).execute(school_id=v.id, name="B", email="a@t.com",
                                                hashed_password="h", role=UserRole.manager)


def test_create_staff_enforces_coach_limit():
    repo, uow = FakePlatform(), FakeUoW()
    v = _school(repo, uow)  # trial license max_coaches=2
    repo.counts[v.id] = (0, 2, 0)  # already at limit
    with pytest.raises(uc.CoachLimitReached):
        uc.CreateStaff(repo, FakeUoW()).execute(school_id=v.id, name="C", email="c@t.com",
                                                hashed_password="h", role=UserRole.coach)


def test_create_staff_manager_not_limited_by_coach_cap():
    repo, uow = FakePlatform(), FakeUoW()
    v = _school(repo, uow)
    repo.counts[v.id] = (0, 2, 0)
    m = uc.CreateStaff(repo, FakeUoW()).execute(school_id=v.id, name="M", email="m@t.com",
                                                hashed_password="h", role=UserRole.manager)
    assert m.role == UserRole.manager


def test_delete_staff_wrong_school_raises():
    repo, uow = FakePlatform(), FakeUoW()
    v = _school(repo, uow)
    m = uc.CreateStaff(repo, FakeUoW()).execute(school_id=v.id, name="A", email="a@t.com",
                                                hashed_password="h", role=UserRole.manager)
    with pytest.raises(uc.StaffNotFound):
        uc.DeleteStaff(repo, FakeUoW()).execute(school_id="OUTRA", user_id=m.id)
