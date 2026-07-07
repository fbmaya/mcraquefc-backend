import pytest
from app.shared.domain.value_objects import Email
from app.shared.domain.errors import ValidationError


def test_email_normalizes_lower_and_strip():
    assert Email.parse("  PAI@Teste.COM ").value == "pai@teste.com"


def test_email_equality_by_value():
    assert Email.parse("a@b.com") == Email.parse("A@B.COM")


def test_invalid_email_raises():
    with pytest.raises(ValidationError):
        Email.parse("naoehemail")


def test_empty_email_raises():
    with pytest.raises(ValidationError):
        Email.parse("")


def test_try_parse_returns_none_for_empty():
    assert Email.try_parse("") is None
    assert Email.try_parse(None) is None
    assert Email.try_parse("  a@b.com ").value == "a@b.com"
