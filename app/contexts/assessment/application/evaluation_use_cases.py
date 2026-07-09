from app.shared.domain.errors import DomainError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.contexts.assessment.domain.evaluation import Evaluation
from app.contexts.assessment.domain.repositories import EvaluationRepository
from app.contexts.assessment.application.evaluation_dtos import NewEvaluation, EvaluationView


class StudentNotFound(DomainError):
    pass


class EvaluationNotFound(DomainError):
    pass


class CreateEvaluation:
    def __init__(self, evaluations: EvaluationRepository, uow: UnitOfWork):
        self.evaluations, self.uow = evaluations, uow

    def execute(self, *, school_id: str, evaluated_by: str, data: NewEvaluation) -> EvaluationView:
        if not self.evaluations.student_belongs_to_school(data.student_id, school_id):
            raise StudentNotFound("Aluno não encontrado")
        evaluation = Evaluation.register(
            id=self.evaluations.next_id(), student_id=data.student_id, date=data.date,
            skills=data.skills, evaluated_by=evaluated_by, notes=data.notes,
        )
        self.evaluations.add(evaluation)
        self.uow.commit()
        saved = self.evaluations.get(evaluation.id)  # relê p/ created_at
        return EvaluationView.of(saved)


class ListEvaluations:
    def __init__(self, evaluations: EvaluationRepository):
        self.evaluations = evaluations

    def execute(self, *, school_id: str, student_id: str | None = None) -> list[EvaluationView]:
        return [EvaluationView.of(e) for e in self.evaluations.list_by_school(school_id, student_id)]


class ListEvaluationsForStudent:
    """Portal do responsável: avaliações de um aluno (sem escopo de escola)."""

    def __init__(self, evaluations: EvaluationRepository):
        self.evaluations = evaluations

    def execute(self, *, student_id: str) -> list[EvaluationView]:
        return [EvaluationView.of(e) for e in self.evaluations.list_by_student(student_id)]


class DeleteEvaluation:
    def __init__(self, evaluations: EvaluationRepository, uow: UnitOfWork):
        self.evaluations, self.uow = evaluations, uow

    def execute(self, *, school_id: str, evaluation_id: str) -> None:
        evaluation = self.evaluations.get(evaluation_id)
        if evaluation is None or not self.evaluations.student_belongs_to_school(evaluation.student_id, school_id):
            raise EvaluationNotFound("Avaliação não encontrada")
        self.evaluations.remove(evaluation)
        self.uow.commit()
