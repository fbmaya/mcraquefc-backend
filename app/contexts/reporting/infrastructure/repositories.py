"""Read model do contexto Reporting.

Conjuntos de dados são pequenos (por escola), então agregações rodam em Python
por clareza, em vez de empurrar tudo para SQL.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.class_ import Class, ClassEnrollment
from app.models.evaluation import Evaluation
from app.models.attendance import AttendanceRecord
from app.models.match import Match, MatchStat
from app.contexts.reporting.domain.read_models import SUMMARY_AXES, StudentRef, EvalSnapshot
from app.contexts.reporting.domain.repositories import ReportingRepository


def _round1(value):
    return round(float(value), 1) if value is not None else None


def _axes(ev: Evaluation) -> list:
    return [getattr(ev, axis) for axis in SUMMARY_AXES]


class SqlAlchemyReportingRepository(ReportingRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_student(self, student_id: str) -> StudentRef | None:
        row = self.session.get(Student, student_id)
        if row is None:
            return None
        return StudentRef(id=row.id, name=row.name, position=row.position, school_id=row.school_id)

    def class_info(self, student_id: str) -> tuple[str | None, str | None]:
        row = (
            self.session.query(Class.name, Class.age_group)
            .join(ClassEnrollment, ClassEnrollment.class_id == Class.id)
            .filter(ClassEnrollment.student_id == student_id, ClassEnrollment.active == True)  # noqa: E712
            .first()
        )
        return (row[0], row[1]) if row else (None, None)

    def evaluations_desc(self, student_id: str) -> list[EvalSnapshot]:
        rows = (
            self.session.query(Evaluation)
            .filter(Evaluation.student_id == student_id)
            .order_by(Evaluation.date.desc(), Evaluation.created_at.desc())
            .all()
        )
        return [EvalSnapshot(date=ev.date, overall=ev.overall, axes=_axes(ev)) for ev in rows]

    def latest_axes(self, student_id: str) -> list[float | None] | None:
        ev = (
            self.session.query(Evaluation)
            .filter(Evaluation.student_id == student_id)
            .order_by(Evaluation.date.desc(), Evaluation.created_at.desc())
            .first()
        )
        return _axes(ev) if ev else None

    def attendance_summary(self, student_id: str) -> dict:
        total = (
            self.session.query(func.count(AttendanceRecord.id))
            .filter(AttendanceRecord.student_id == student_id)
            .scalar()
        ) or 0
        present = (
            self.session.query(func.count(AttendanceRecord.id))
            .filter(AttendanceRecord.student_id == student_id, AttendanceRecord.present == True)  # noqa: E712
            .scalar()
        ) or 0
        rate = round(present / total * 100, 1) if total else None
        return {"sessions": total, "present": present, "absent": total - present, "rate": rate}

    def match_summary(self, student_id: str) -> dict:
        row = (
            self.session.query(
                func.coalesce(func.sum(MatchStat.goals), 0),
                func.coalesce(func.sum(MatchStat.assists), 0),
                func.coalesce(func.sum(MatchStat.yellow_cards), 0),
                func.coalesce(func.sum(MatchStat.red_cards), 0),
                func.count(MatchStat.id).filter(MatchStat.played == True),  # noqa: E712
                func.avg(MatchStat.rating),
            )
            .filter(MatchStat.student_id == student_id)
            .first()
        )
        goals, assists, yellows, reds, played, avg_rating = row
        return {
            "goals": int(goals),
            "assists": int(assists),
            "yellow_cards": int(yellows),
            "red_cards": int(reds),
            "matches_played": int(played or 0),
            "avg_rating": _round1(avg_rating),
        }

    def _peer_ids(self, school_id: str, column, value) -> set[str]:
        rows = (
            self.session.query(ClassEnrollment.student_id)
            .join(Class, Class.id == ClassEnrollment.class_id)
            .filter(
                Class.school_id == school_id,
                column == value,
                ClassEnrollment.active == True,  # noqa: E712
            )
            .all()
        )
        return {r[0] for r in rows}

    def class_peer_ids(self, school_id: str, class_name: str) -> set[str]:
        return self._peer_ids(school_id, Class.name, class_name)

    def category_peer_ids(self, school_id: str, category: str) -> set[str]:
        return self._peer_ids(school_id, Class.age_group, category)

    def school_overview(self, school_id: str) -> dict:
        total_students = (
            self.session.query(func.count(Student.id)).filter(Student.school_id == school_id).scalar()
        ) or 0
        total_classes = (
            self.session.query(func.count(Class.id)).filter(Class.school_id == school_id).scalar()
        ) or 0
        att_total = (
            self.session.query(func.count(AttendanceRecord.id))
            .join(Student, Student.id == AttendanceRecord.student_id)
            .filter(Student.school_id == school_id)
            .scalar()
        ) or 0
        att_present = (
            self.session.query(func.count(AttendanceRecord.id))
            .join(Student, Student.id == AttendanceRecord.student_id)
            .filter(Student.school_id == school_id, AttendanceRecord.present == True)  # noqa: E712
            .scalar()
        ) or 0
        attendance_rate = round(att_present / att_total * 100, 1) if att_total else None
        total_matches = (
            self.session.query(func.count(Match.id)).filter(Match.school_id == school_id).scalar()
        ) or 0
        total_evaluations = (
            self.session.query(func.count(Evaluation.id))
            .join(Student, Student.id == Evaluation.student_id)
            .filter(Student.school_id == school_id)
            .scalar()
        ) or 0
        return {
            "total_students": int(total_students),
            "total_classes": int(total_classes),
            "total_matches": int(total_matches),
            "total_evaluations": int(total_evaluations),
            "attendance_rate": attendance_rate,
        }

    def top_scorers(self, school_id: str, limit: int = 5) -> list[dict]:
        rows = (
            self.session.query(
                Student.id,
                Student.name,
                func.coalesce(func.sum(MatchStat.goals), 0).label("goals"),
                func.coalesce(func.sum(MatchStat.assists), 0).label("assists"),
            )
            .join(MatchStat, MatchStat.student_id == Student.id)
            .filter(Student.school_id == school_id)
            .group_by(Student.id, Student.name)
            .order_by(func.sum(MatchStat.goals).desc())
            .limit(limit)
            .all()
        )
        return [
            {"student_id": r[0], "name": r[1], "goals": int(r[2]), "assists": int(r[3])}
            for r in rows
            if int(r[2]) > 0 or int(r[3]) > 0
        ]
