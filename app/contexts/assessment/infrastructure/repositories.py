import uuid

from sqlalchemy.orm import Session

from app.contexts.assessment.domain.evaluation import Evaluation, SKILLS
from app.contexts.assessment.domain.repositories import EvaluationRepository
from app.models.evaluation import Evaluation as EvaluationORM
from app.models.student import Student as StudentORM


def _to_domain(row: EvaluationORM) -> Evaluation:
    return Evaluation(
        id=row.id, student_id=row.student_id, date=row.date, evaluated_by=row.evaluated_by,
        notes=row.notes, created_at=row.created_at,
        **{k: getattr(row, k) for k in SKILLS},
    )


class SqlAlchemyEvaluationRepository(EvaluationRepository):
    def __init__(self, session: Session):
        self.session = session

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def add(self, evaluation: Evaluation) -> None:
        self.session.add(EvaluationORM(
            id=evaluation.id, student_id=evaluation.student_id, date=evaluation.date,
            evaluated_by=evaluation.evaluated_by, notes=evaluation.notes,
            **{k: getattr(evaluation, k) for k in SKILLS},
        ))

    def get(self, evaluation_id: str) -> Evaluation | None:
        row = self.session.get(EvaluationORM, evaluation_id)
        return _to_domain(row) if row else None

    def list_by_school(self, school_id: str, student_id: str | None = None) -> list[Evaluation]:
        q = (
            self.session.query(EvaluationORM)
            .join(StudentORM, EvaluationORM.student_id == StudentORM.id)
            .filter(StudentORM.school_id == school_id)
        )
        if student_id:
            q = q.filter(EvaluationORM.student_id == student_id)
        return [_to_domain(r) for r in q.order_by(EvaluationORM.date.desc()).all()]

    def list_by_student(self, student_id: str) -> list[Evaluation]:
        rows = (
            self.session.query(EvaluationORM)
            .filter(EvaluationORM.student_id == student_id)
            .order_by(EvaluationORM.date.desc())
            .all()
        )
        return [_to_domain(r) for r in rows]

    def remove(self, evaluation: Evaluation) -> None:
        row = self.session.get(EvaluationORM, evaluation.id)
        if row:
            self.session.delete(row)

    def student_belongs_to_school(self, student_id: str, school_id: str) -> bool:
        row = self.session.get(StudentORM, student_id)
        return row is not None and row.school_id == school_id
