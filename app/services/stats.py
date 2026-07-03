"""Aggregation / statistics helpers shared by the /stats router and the parent portal.

Datasets are scoped per school (small), so aggregations run in Python for clarity
rather than pushing every computation into SQL.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.class_ import Class, ClassEnrollment
from app.models.evaluation import Evaluation
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.match import Match, MatchStat

# Order matters: this is the radar's axis order (matches the frontend).
SUMMARY_AXES = ["technique", "physical", "tactical", "mindset", "discipline", "teamwork"]


def _round1(value):
    return round(float(value), 1) if value is not None else None


# ── Student context ─────────────────────────────────────────────

def student_class_info(db: Session, student_id: str):
    """Return (class_name, category) from the student's first active enrollment."""
    row = (
        db.query(Class.name, Class.age_group)
        .join(ClassEnrollment, ClassEnrollment.class_id == Class.id)
        .filter(ClassEnrollment.student_id == student_id, ClassEnrollment.active == True)  # noqa: E712
        .first()
    )
    if not row:
        return None, None
    return row[0], row[1]


def latest_evaluation(db: Session, student_id: str) -> Evaluation | None:
    return (
        db.query(Evaluation)
        .filter(Evaluation.student_id == student_id)
        .order_by(Evaluation.date.desc(), Evaluation.created_at.desc())
        .first()
    )


def _axes_values(ev: Evaluation | None):
    if ev is None:
        return None
    return [getattr(ev, axis) for axis in SUMMARY_AXES]


# ── Aggregations ────────────────────────────────────────────────

def attendance_summary(db: Session, student_id: str) -> dict:
    total = (
        db.query(func.count(AttendanceRecord.id))
        .filter(AttendanceRecord.student_id == student_id)
        .scalar()
    ) or 0
    present = (
        db.query(func.count(AttendanceRecord.id))
        .filter(AttendanceRecord.student_id == student_id, AttendanceRecord.present == True)  # noqa: E712
        .scalar()
    ) or 0
    rate = round(present / total * 100, 1) if total else None
    return {"sessions": total, "present": present, "absent": total - present, "rate": rate}


def match_summary(db: Session, student_id: str) -> dict:
    row = (
        db.query(
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


def student_performance(db: Session, student: Student) -> dict:
    """Full performance snapshot for one child — what a parent/coach dashboard shows."""
    current = latest_evaluation(db, student.id)
    history = (
        db.query(Evaluation)
        .filter(Evaluation.student_id == student.id)
        .order_by(Evaluation.date.desc(), Evaluation.created_at.desc())
        .all()
    )
    previous = history[1] if len(history) > 1 else None

    class_name, category = student_class_info(db, student.id)

    current_axes = _axes_values(current)
    previous_axes = _axes_values(previous)
    overall_delta = None
    if current and previous and current.overall is not None and previous.overall is not None:
        overall_delta = round(current.overall - previous.overall, 1)

    return {
        "student_id": student.id,
        "name": student.name,
        "position": student.position,
        "class_name": class_name,
        "category": category,
        "evaluations_count": len(history),
        "radar": {
            "axes": SUMMARY_AXES,
            "current": current_axes,
            "previous": previous_axes,
        },
        "overall": current.overall if current else None,
        "overall_delta": overall_delta,
        "last_evaluation_date": current.date.isoformat() if current else None,
        "attendance": attendance_summary(db, student.id),
        "matches": match_summary(db, student.id),
    }


def _average_axes(rows: list[list]) -> list:
    """Average a list of axis-value lists, ignoring None per position."""
    if not rows:
        return [None] * len(SUMMARY_AXES)
    out = []
    for i in range(len(SUMMARY_AXES)):
        present = [r[i] for r in rows if r[i] is not None]
        out.append(round(sum(present) / len(present), 1) if present else None)
    return out


def peer_averages(db: Session, student: Student) -> dict:
    """Class and category (age group) averages per radar axis, for comparison."""
    class_name, category = student_class_info(db, student.id)

    # classmates: students sharing an active class with this student
    class_student_ids = set()
    if class_name is not None:
        rows = (
            db.query(ClassEnrollment.student_id)
            .join(Class, Class.id == ClassEnrollment.class_id)
            .filter(
                Class.school_id == student.school_id,
                Class.name == class_name,
                ClassEnrollment.active == True,  # noqa: E712
            )
            .all()
        )
        class_student_ids = {r[0] for r in rows}

    # category peers: students whose active class shares the age group
    category_student_ids = set()
    if category is not None:
        rows = (
            db.query(ClassEnrollment.student_id)
            .join(Class, Class.id == ClassEnrollment.class_id)
            .filter(
                Class.school_id == student.school_id,
                Class.age_group == category,
                ClassEnrollment.active == True,  # noqa: E712
            )
            .all()
        )
        category_student_ids = {r[0] for r in rows}

    def axes_for(ids: set) -> list:
        rows = []
        for sid in ids:
            axes = _axes_values(latest_evaluation(db, sid))
            if axes is not None:
                rows.append(axes)
        return _average_axes(rows)

    return {
        "axes": SUMMARY_AXES,
        "class_name": class_name,
        "category": category,
        "class_avg": axes_for(class_student_ids),
        "category_avg": axes_for(category_student_ids),
        "class_size": len(class_student_ids),
        "category_size": len(category_student_ids),
    }


def school_overview(db: Session, school_id: str) -> dict:
    """Headline KPIs for the school dashboard."""
    students = db.query(Student).filter(Student.school_id == school_id).all()
    student_ids = [s.id for s in students]

    total_students = len(students)
    total_classes = db.query(func.count(Class.id)).filter(Class.school_id == school_id).scalar() or 0

    # attendance rate across the whole school
    att_total = (
        db.query(func.count(AttendanceRecord.id))
        .join(Student, Student.id == AttendanceRecord.student_id)
        .filter(Student.school_id == school_id)
        .scalar()
    ) or 0
    att_present = (
        db.query(func.count(AttendanceRecord.id))
        .join(Student, Student.id == AttendanceRecord.student_id)
        .filter(Student.school_id == school_id, AttendanceRecord.present == True)  # noqa: E712
        .scalar()
    ) or 0
    attendance_rate = round(att_present / att_total * 100, 1) if att_total else None

    total_matches = db.query(func.count(Match.id)).filter(Match.school_id == school_id).scalar() or 0
    total_evaluations = (
        db.query(func.count(Evaluation.id))
        .join(Student, Student.id == Evaluation.student_id)
        .filter(Student.school_id == school_id)
        .scalar()
    ) or 0

    return {
        "total_students": total_students,
        "total_classes": int(total_classes),
        "total_matches": int(total_matches),
        "total_evaluations": int(total_evaluations),
        "attendance_rate": attendance_rate,
    }


def top_scorers(db: Session, school_id: str, limit: int = 5) -> list[dict]:
    rows = (
        db.query(
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
