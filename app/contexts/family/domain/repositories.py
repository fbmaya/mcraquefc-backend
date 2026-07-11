from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.contexts.family.domain.subscription import FamilySubscription


@dataclass(frozen=True)
class StudentAccessInfo:
    active: bool
    school_id: str


class FamilySubscriptionRepository(ABC):
    @abstractmethod
    def next_id(self) -> str: ...
    @abstractmethod
    def add(self, sub: FamilySubscription) -> None: ...
    @abstractmethod
    def save(self, sub: FamilySubscription) -> None: ...
    @abstractmethod
    def get(self, sub_id: str) -> FamilySubscription | None: ...
    @abstractmethod
    def active_for(self, parent_id: str, school_id: str) -> FamilySubscription | None:
        """Assinatura NÃO-cancelada do responsável naquela escola (p/ o gate e p/ evitar duplicidade)."""
    @abstractmethod
    def list_by_school(self, school_id: str) -> list[FamilySubscription]: ...


class FamilyAccessReader(ABC):
    """Porta de leitura cross-context para a regra de acesso (não escreve)."""

    @abstractmethod
    def is_linked(self, parent_id: str, student_id: str) -> bool: ...
    @abstractmethod
    def student_access_info(self, student_id: str) -> StudentAccessInfo | None:
        """(active, school_id) do aluno, ou None se não existe."""
    @abstractmethod
    def school_family_included(self, school_id: str) -> bool:
        """True se a escola tem Family incluso E está ativa E licença ativa (Caminho 1)."""
