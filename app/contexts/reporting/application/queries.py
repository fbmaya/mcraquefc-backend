from app.shared.domain.errors import DomainError
from app.contexts.reporting.domain.read_models import SUMMARY_AXES
from app.contexts.reporting.domain.repositories import ReportingRepository


class StudentNotFound(DomainError):
    pass


def _average_axes(rows: list[list]) -> list:
    """Média de várias listas de eixos, ignorando None por posição."""
    if not rows:
        return [None] * len(SUMMARY_AXES)
    out = []
    for i in range(len(SUMMARY_AXES)):
        present = [r[i] for r in rows if r[i] is not None]
        out.append(round(sum(present) / len(present), 1) if present else None)
    return out


class StudentPerformance:
    """Snapshot completo de desempenho de um aluno (dashboard pai/professor)."""

    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def execute(self, *, student_id: str, school_id: str | None = None) -> dict:
        ref = self.repo.get_student(student_id)
        if ref is None or (school_id is not None and ref.school_id != school_id):
            raise StudentNotFound("Aluno não encontrado")

        history = self.repo.evaluations_desc(student_id)
        current = history[0] if history else None
        previous = history[1] if len(history) > 1 else None

        class_name, category = self.repo.class_info(student_id)

        overall_delta = None
        if current and previous and current.overall is not None and previous.overall is not None:
            overall_delta = round(current.overall - previous.overall, 1)

        return {
            "student_id": ref.id,
            "name": ref.name,
            "position": ref.position,
            "class_name": class_name,
            "category": category,
            "evaluations_count": len(history),
            "radar": {
                "axes": SUMMARY_AXES,
                "current": current.axes if current else None,
                "previous": previous.axes if previous else None,
            },
            "overall": current.overall if current else None,
            "overall_delta": overall_delta,
            "last_evaluation_date": current.date.isoformat() if current and current.date else None,
            "attendance": self.repo.attendance_summary(student_id),
            "matches": self.repo.match_summary(student_id),
        }


class PeerAverages:
    """Médias por eixo do radar para a turma e a categoria (faixa etária)."""

    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def execute(self, *, student_id: str, school_id: str | None = None) -> dict:
        ref = self.repo.get_student(student_id)
        if ref is None or (school_id is not None and ref.school_id != school_id):
            raise StudentNotFound("Aluno não encontrado")

        class_name, category = self.repo.class_info(student_id)
        class_ids = self.repo.class_peer_ids(ref.school_id, class_name) if class_name else set()
        category_ids = self.repo.category_peer_ids(ref.school_id, category) if category else set()

        def axes_for(ids: set) -> list:
            rows = [a for a in (self.repo.latest_axes(sid) for sid in ids) if a is not None]
            return _average_axes(rows)

        return {
            "axes": SUMMARY_AXES,
            "class_name": class_name,
            "category": category,
            "class_avg": axes_for(class_ids),
            "category_avg": axes_for(category_ids),
            "class_size": len(class_ids),
            "category_size": len(category_ids),
        }


class SchoolOverview:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def execute(self, *, school_id: str) -> dict:
        data = self.repo.school_overview(school_id)
        data["top_scorers"] = self.repo.top_scorers(school_id)
        return data


class Leaderboard:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def execute(self, *, school_id: str, limit: int = 10) -> dict:
        return {"top_scorers": self.repo.top_scorers(school_id, limit=limit)}
