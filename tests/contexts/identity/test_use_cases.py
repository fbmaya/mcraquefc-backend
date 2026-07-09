import pytest
from app.auth.jwt import hash_password
from app.models.user import UserRole
from app.contexts.identity.domain.user import User
from app.contexts.identity.domain.repositories import UserRepository, ParentLinkRepository
from app.contexts.identity.application import use_cases as uc


class FakeUsers(UserRepository):
    def __init__(self):
        self.items: dict[str, User] = {}
        self._n = 0

    def next_id(self):
        self._n += 1
        return f"u{self._n}"

    def get(self, uid): return self.items.get(uid)
    def get_by_email(self, email): return next((u for u in self.items.values() if u.email == email), None)
    def find_by_email_ci(self, email):
        return next((u for u in self.items.values() if u.email.lower() == email.strip().lower()), None)
    def email_exists(self, email): return any(u.email == email for u in self.items.values())
    def add(self, user): self.items[user.id] = user
    def save(self, user): self.items[user.id] = user


class FakeLinks(ParentLinkRepository):
    def __init__(self, students_by_email=None):
        self.students_by_email = students_by_email or {}   # email(lower) -> [student_id]
        self.links: set[tuple] = set()                     # (parent_id, student_id)
        self._n = 0

    def next_id(self):
        self._n += 1
        return f"l{self._n}"

    def student_ids_for_guardian_email(self, email):
        return list(self.students_by_email.get(email.strip().lower(), []))

    def linked_student_ids(self, parent_id):
        return {sid for (pid, sid) in self.links if pid == parent_id}

    def add_link(self, link_id, parent_id, student_id):
        self.links.add((parent_id, student_id))


class FakeUoW:
    def __init__(self): self.commits = 0
    def commit(self): self.commits += 1
    def rollback(self): pass


# ── RegisterParent ────────────────────────────────────────────

def test_register_parent_creates_and_reconciles():
    users = FakeUsers()
    links = FakeLinks(students_by_email={"mae@t.com": ["stu1", "stu2"]})
    view = uc.RegisterParent(users, links, FakeUoW()).execute(
        name="Mãe", email="mae@t.com", hashed_password="h", role=UserRole.parent)
    assert view.role == UserRole.parent and view.school_id is None
    # vínculos criados por reconciliação
    assert links.linked_student_ids(view.id) == {"stu1", "stu2"}


def test_register_duplicate_email_raises_before_role_check():
    users = FakeUsers()
    users.add(User.register_parent(id="x", name="A", email="a@t.com", hashed_password="h"))
    # mesmo com papel != parent, o email duplicado (400) vem primeiro
    with pytest.raises(uc.EmailAlreadyUsed):
        uc.RegisterParent(users, FakeLinks(), FakeUoW()).execute(
            name="B", email="a@t.com", hashed_password="h", role=UserRole.manager)


def test_register_non_parent_role_rejected():
    with pytest.raises(uc.PublicRegistrationParentOnly):
        uc.RegisterParent(FakeUsers(), FakeLinks(), FakeUoW()).execute(
            name="Chefe", email="chefe@t.com", hashed_password="h", role=UserRole.manager)


# ── AuthenticatePassword ──────────────────────────────────────

def test_authenticate_success():
    users = FakeUsers()
    users.add(User.register_parent(id="u1", name="A", email="a@t.com", hashed_password=hash_password("secret")))
    view = uc.AuthenticatePassword(users).execute(email="a@t.com", password="secret")
    assert view.id == "u1"


def test_authenticate_wrong_password():
    users = FakeUsers()
    users.add(User.register_parent(id="u1", name="A", email="a@t.com", hashed_password=hash_password("secret")))
    with pytest.raises(uc.InvalidCredentials):
        uc.AuthenticatePassword(users).execute(email="a@t.com", password="nope")


def test_authenticate_unknown_email():
    with pytest.raises(uc.InvalidCredentials):
        uc.AuthenticatePassword(FakeUsers()).execute(email="ghost@t.com", password="x")


def test_authenticate_google_only_user_has_no_password():
    users = FakeUsers()
    users.add(User.provision_google_parent(id="u1", name="A", email="a@t.com", google_sub="s"))
    with pytest.raises(uc.InvalidCredentials):
        uc.AuthenticatePassword(users).execute(email="a@t.com", password="anything")


# ── GoogleUpsert ──────────────────────────────────────────────

def test_google_provisions_new_parent():
    users = FakeUsers()
    view = uc.GoogleUpsert(users, FakeUoW()).execute(email="new@t.com", sub="sub1", name="Novo")
    assert view.email == "new@t.com" and view.role == UserRole.parent
    assert users.find_by_email_ci("new@t.com").google_sub == "sub1"


def test_google_links_sub_to_existing_user():
    users = FakeUsers()
    users.add(User.register_parent(id="u1", name="A", email="a@t.com", hashed_password="h"))
    uow = FakeUoW()
    view = uc.GoogleUpsert(users, uow).execute(email="a@t.com", sub="sub1", name="A")
    assert view.id == "u1" and users.get("u1").google_sub == "sub1"
    assert uow.commits == 1


def test_google_matches_case_insensitively():
    users = FakeUsers()
    users.add(User.register_parent(id="u1", name="A", email="A@T.com", hashed_password="h"))
    view = uc.GoogleUpsert(users, FakeUoW()).execute(email="a@t.com", sub="s", name="A")
    assert view.id == "u1"  # não cria duplicado


# ── ReconcileParentLinks ──────────────────────────────────────

def test_reconcile_skips_non_parent():
    links = FakeLinks(students_by_email={"a@t.com": ["stu1"]})
    created = uc.ReconcileParentLinks(links, FakeUoW()).execute(
        user_id="u1", email="a@t.com", role=UserRole.manager)
    assert created == 0


def test_reconcile_only_creates_missing():
    links = FakeLinks(students_by_email={"a@t.com": ["stu1", "stu2"]})
    links.links.add(("u1", "stu1"))  # já vinculado
    uow = FakeUoW()
    created = uc.ReconcileParentLinks(links, uow).execute(user_id="u1", email="a@t.com", role=UserRole.parent)
    assert created == 1 and links.linked_student_ids("u1") == {"stu1", "stu2"}
    assert uow.commits == 1
