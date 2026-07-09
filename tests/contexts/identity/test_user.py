import pytest
from app.shared.domain.errors import ValidationError
from app.models.user import UserRole
from app.contexts.identity.domain.user import User


def test_register_parent_requires_name():
    with pytest.raises(ValidationError):
        User.register_parent(id="u1", name="  ", email="p@t.com", hashed_password="h")


def test_register_parent_sets_role_and_no_school():
    u = User.register_parent(id="u1", name="Mãe", email="mae@t.com", hashed_password="h")
    assert u.role == UserRole.parent and u.school_id is None
    assert u.name == "Mãe" and u.hashed_password == "h"


def test_provision_google_parent_has_no_password():
    u = User.provision_google_parent(id="u1", name="Ana", email="ana@t.com", google_sub="sub1")
    assert u.hashed_password is None and u.google_sub == "sub1" and u.role == UserRole.parent


def test_link_google_sets_only_when_absent():
    u = User.register_parent(id="u1", name="X", email="x@t.com", hashed_password="h")
    assert u.link_google("sub1") is True and u.google_sub == "sub1"
    assert u.link_google("sub2") is False and u.google_sub == "sub1"  # não sobrescreve
    assert u.link_google(None) is False
