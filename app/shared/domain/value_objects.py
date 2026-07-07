import re
from dataclasses import dataclass

from app.shared.domain.base import ValueObject
from app.shared.domain.errors import ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Email(ValueObject):
    value: str

    @classmethod
    def parse(cls, raw: str | None) -> "Email":
        normalized = (raw or "").strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValidationError(f"E-mail inválido: {raw!r}")
        return cls(normalized)

    @classmethod
    def try_parse(cls, raw: str | None) -> "Email | None":
        if not raw or not raw.strip():
            return None
        return cls.parse(raw)
