from abc import ABC, abstractmethod

from app.contexts.identity.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    def next_id(self) -> str: ...
    @abstractmethod
    def get(self, user_id: str) -> User | None: ...
    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Busca exata por email (usada no login)."""
    @abstractmethod
    def find_by_email_ci(self, email: str) -> User | None:
        """Busca case-insensitive (usada no login Google)."""
    @abstractmethod
    def email_exists(self, email: str) -> bool: ...
    @abstractmethod
    def add(self, user: User) -> None: ...
    @abstractmethod
    def save(self, user: User) -> None: ...


class ParentLinkRepository(ABC):
    @abstractmethod
    def next_id(self) -> str: ...
    @abstractmethod
    def student_ids_for_guardian_email(self, email: str) -> list[str]: ...
    @abstractmethod
    def linked_student_ids(self, parent_id: str) -> set[str]: ...
    @abstractmethod
    def add_link(self, link_id: str, parent_id: str, student_id: str) -> None: ...
