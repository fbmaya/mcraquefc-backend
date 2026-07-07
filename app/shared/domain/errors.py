class DomainError(Exception):
    """Erro de regra de domínio (esperado, não é bug de infra)."""


class ValidationError(DomainError):
    """Valor inválido para uma regra/invariante de domínio."""
