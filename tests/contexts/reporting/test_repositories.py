import datetime as dt
import uuid
from app.models.school import School
from app.models.student import Student
from app.models.class_ import Class, ClassEnrollment
from app.models.evaluation import Evaluation
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.match import Match, MatchStat
from app.contexts.reporting.infrastructure.repositories import SqlAlchemyReportingRepository


def _seed(db):
    school = School(id=str(uuid.uuid4()), name="E", primary_color="#000")
    db.add(school)
    cls = Class(id=str(uuid.uuid4()), school_id=school.id, name="Sub-9", age_group="U9")
    db.add(cls)
    stu = Student(id=str(uuid.uuid4()), school_id=school.id, name="Lucas",
                  position="ATA", guardian_email="p@t.com")
    db.add(stu)
    db.add(ClassEnrollment(id=str(uuid.uuid4()), class_id=cls.id, student_id=stu.id, active=True))
    # two evaluations (radar current/previous)
    db.add(Evaluation(id=str(uuid.uuid4()), student_id=stu.id, date=dt.date(2026, 5, 1),
                      passing=6, finishing=6, dribbling=6, discipline=6, teamwork=6, speed=6))
    db.add(Evaluation(id=str(uuid.uuid4()), student_id=stu.id, date=dt.date(2026, 6, 1),
                      passing=8, finishing=8, dribbling=8, discipline=9, teamwork=7, speed=9))
    # attendance: 2 sessions, 1 present
    sess = AttendanceSession(id=str(uuid.uuid4()), class_id=cls.id, date=dt.date(2026, 6, 1))
    db.add(sess)
    db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=sess.id, student_id=stu.id, present=True))
    db.add(AttendanceRecord(id=str(uuid.uuid4()), session_id=sess.id, student_id=stu.id, present=False))
    # match with stats
    m = Match(id=str(uuid.uuid4()), school_id=school.id, date=dt.date(2026, 6, 1), opponent="Rival")
    db.add(m)
    db.add(MatchStat(id=str(uuid.uuid4()), match_id=m.id, student_id=stu.id,
                     goals=3, assists=1, played=True, rating=8.0))
    db.commit()
    return school.id, stu.id


def test_get_student_and_class_info(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyReportingRepository(db_session)
    ref = repo.get_student(stu_id)
    assert ref is not None and ref.name == "Lucas" and ref.position == "ATA" and ref.school_id == school_id
    assert repo.get_student("ghost") is None
    assert repo.class_info(stu_id) == ("Sub-9", "U9")


def test_evaluations_desc_and_latest_axes(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyReportingRepository(db_session)
    evs = repo.evaluations_desc(stu_id)
    assert [e.date for e in evs] == [dt.date(2026, 6, 1), dt.date(2026, 5, 1)]  # desc
    assert evs[0].overall is not None
    # latest axes = 6 values (SUMMARY_AXES order), technique = (8+8+8)/3 = 8.0
    axes = repo.latest_axes(stu_id)
    assert len(axes) == 6 and axes[0] == 8.0


def test_attendance_and_match_summary(db_session):
    _, stu_id = _seed(db_session)
    repo = SqlAlchemyReportingRepository(db_session)
    att = repo.attendance_summary(stu_id)
    assert att == {"sessions": 2, "present": 1, "absent": 1, "rate": 50.0}
    ms = repo.match_summary(stu_id)
    assert ms["goals"] == 3 and ms["assists"] == 1 and ms["matches_played"] == 1 and ms["avg_rating"] == 8.0


def test_peer_ids_and_overview_and_scorers(db_session):
    school_id, stu_id = _seed(db_session)
    repo = SqlAlchemyReportingRepository(db_session)
    assert repo.class_peer_ids(school_id, "Sub-9") == {stu_id}
    assert repo.category_peer_ids(school_id, "U9") == {stu_id}
    ov = repo.school_overview(school_id)
    assert ov["total_students"] == 1 and ov["total_classes"] == 1 and ov["total_matches"] == 1
    assert ov["total_evaluations"] == 2 and ov["attendance_rate"] == 50.0
    scorers = repo.top_scorers(school_id)
    assert scorers[0]["student_id"] == stu_id and scorers[0]["goals"] == 3
