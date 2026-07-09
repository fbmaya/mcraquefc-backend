from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.auth.jwt import verify_password  # utilitário técnico (kernel compartilhado)
from app.models.user import UserRole
from app.contexts.identity.domain.user import User
from app.contexts.identity.domain.repositories import UserRepository, ParentLinkRepository
from app.contexts.identity.application.dtos import UserView


class EmailAlreadyUsed(DomainError):
    pass


class PublicRegistrationParentOnly(DomainError):
    pass


class InvalidCredentials(DomainError):
    pass


class ReconcileParentLinks:
    """Cria os vínculos pai↔aluno que faltam batendo guardian_email == email do responsável."""

    def __init__(self, links: ParentLinkRepository, uow: UnitOfWork):
        self.links, self.uow = links, uow

    def execute(self, *, user_id: str, email: str, role: UserRole) -> int:
        if role != UserRole.parent or not email:
            return 0
        email_n = email.strip().lower()
        student_ids = self.links.student_ids_for_guardian_email(email_n)
        if not student_ids:
            return 0
        already = self.links.linked_student_ids(user_id)
        created = 0
        for student_id in student_ids:
            if student_id not in already:
                self.links.add_link(self.links.next_id(), user_id, student_id)
                created += 1
        if created:
            self.uow.commit()
        return created


class RegisterParent:
    def __init__(self, users: UserRepository, links: ParentLinkRepository, uow: UnitOfWork):
        self.users, self.links, self.uow = users, links, uow

    def execute(self, *, name: str, email: str, hashed_password: str, role: UserRole) -> UserView:
        # ordem preservada: email duplicado (400) antes da checagem de papel (403)
        if self.users.email_exists(email):
            raise EmailAlreadyUsed("Email já cadastrado")
        if role != UserRole.parent:
            raise PublicRegistrationParentOnly(
                "Registro público disponível apenas para responsáveis. "
                "Gestores e professores são cadastrados pela plataforma."
            )
        user = User.register_parent(id=self.users.next_id(), name=name, email=email,
                                    hashed_password=hashed_password)
        self.users.add(user)
        self.uow.commit()
        ReconcileParentLinks(self.links, self.uow).execute(
            user_id=user.id, email=user.email, role=user.role)
        return UserView.of(user)


class AuthenticatePassword:
    """Valida email+senha. Não faz reconcile nem guard de tenant (a interface orquestra)."""

    def __init__(self, users: UserRepository):
        self.users = users

    def execute(self, *, email: str, password: str) -> UserView:
        user = self.users.get_by_email(email)
        if user is None or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise InvalidCredentials("Email ou senha inválidos")
        return UserView.of(user)


class GoogleUpsert:
    """Acha/cria o usuário por email (case-insensitive) e vincula o google_sub."""

    def __init__(self, users: UserRepository, uow: UnitOfWork):
        self.users, self.uow = users, uow

    def execute(self, *, email: str, sub: str | None, name: str) -> UserView:
        user = self.users.find_by_email_ci(email)
        if user is None:
            user = User.provision_google_parent(id=self.users.next_id(), name=name,
                                                email=email, google_sub=sub)
            self.users.add(user)
            self.uow.commit()
        elif user.link_google(sub):
            self.users.save(user)
            self.uow.commit()
        return UserView.of(user)
