from dataclasses import dataclass
from app.shared.domain.base import ValueObject, Entity, AggregateRoot
from app.shared.domain.errors import DomainError, ValidationError


def test_validation_error_is_domain_error():
    assert issubclass(ValidationError, DomainError)


def test_entities_are_equal_by_id():
    a = Entity(id="x")
    b = Entity(id="x")
    c = Entity(id="y")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)


def test_aggregate_root_is_entity():
    assert issubclass(AggregateRoot, Entity)


def test_value_object_marker_exists():
    @dataclass(frozen=True)
    class Sample(ValueObject):
        v: int
    assert Sample(1) == Sample(1)
