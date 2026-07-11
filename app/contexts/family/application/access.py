import datetime as dt

from app.contexts.family.domain.repositories import FamilySubscriptionRepository, FamilyAccessReader


class CheckFamilyAccess:
    """Regra de acesso Family (compõe os 2 caminhos). Não escreve nada.

    Libera se: o responsável está vinculado ao aluno E o aluno está ativo E
    (Caminho 1: a escola tem Family incluso/ativo) OU (Caminho 2: o responsável
    tem FamilySubscription cobrindo hoje na escola do aluno)."""

    def __init__(self, subs: FamilySubscriptionRepository, reader: FamilyAccessReader):
        self.subs, self.reader = subs, reader

    def execute(self, *, parent_id: str, student_id: str, today: dt.date | None = None) -> bool:
        today = today or dt.date.today()
        if not self.reader.is_linked(parent_id, student_id):
            return False
        info = self.reader.student_access_info(student_id)
        if info is None or not info.active:
            return False
        # Caminho 1 — pacote da escola (automático p/ todos os ativos)
        if self.reader.school_family_included(info.school_id):
            return True
        # Caminho 2 — assinatura individual do responsável naquela escola
        sub = self.subs.active_for(parent_id, info.school_id)
        return sub is not None and sub.covers(today)
