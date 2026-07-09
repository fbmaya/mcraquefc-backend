import datetime as dt
import pytest
from app.contexts.reporting.domain.read_models import StudentRef, EvalSnapshot
from app.contexts.reporting.domain.repositories import ReportingRepository
from app.contexts.reporting.application import queries as q


class FakeReporting(ReportingRepository):
    def __init__(self):
        self.students: dict[str, StudentRef] = {}
        self.evals: dict[str, list[EvalSnapshot]] = {}
        self.classes: dict[str, tuple] = {}          # student_id -> (class_name, category)
        self.latest: dict[str, list] = {}            # student_id -> axes
        self.class_ids: set[str] = set()
        self.category_ids: set[str] = set()
        self.overview_data = {"total_students": 0}
        self.scorers: list[dict] = []

    def get_student(self, sid): return self.students.get(sid)
    def class_info(self, sid): return self.classes.get(sid, (None, None))
    def evaluations_desc(self, sid): return self.evals.get(sid, [])
    def latest_axes(self, sid): return self.latest.get(sid)
    def attendance_summary(self, sid): return {"sessions": 4, "present": 3, "absent": 1, "rate": 75.0}
    def match_summary(self, sid): return {"goals": 2, "assists": 1}
    def class_peer_ids(self, school_id, class_name): return self.class_ids
    def category_peer_ids(self, school_id, category): return self.category_ids
    def school_overview(self, school_id): return dict(self.overview_data)
    def top_scorers(self, school_id, limit=5): return self.scorers[:limit]


def test_student_performance_composes_radar_and_delta():
    repo = FakeReporting()
    repo.students["s1"] = StudentRef(id="s1", name="Lucas", position="ATA", school_id="sch1")
    repo.classes["s1"] = ("Sub-9", "U9")
    repo.evals["s1"] = [
        EvalSnapshot(date=dt.date(2026, 6, 1), overall=8.0, axes=[8, 7, 6, 5, 9, 4]),
        EvalSnapshot(date=dt.date(2026, 5, 1), overall=6.5, axes=[6, 6, 6, 6, 6, 6]),
    ]
    out = q.StudentPerformance(repo).execute(student_id="s1", school_id="sch1")
    assert out["name"] == "Lucas" and out["class_name"] == "Sub-9"
    assert out["evaluations_count"] == 2
    assert out["radar"]["current"] == [8, 7, 6, 5, 9, 4]
    assert out["radar"]["previous"] == [6, 6, 6, 6, 6, 6]
    assert out["overall"] == 8.0 and out["overall_delta"] == 1.5
    assert out["last_evaluation_date"] == "2026-06-01"
    assert out["matches"]["goals"] == 2


def test_student_performance_no_evaluations():
    repo = FakeReporting()
    repo.students["s1"] = StudentRef(id="s1", name="Ana", position=None, school_id="sch1")
    out = q.StudentPerformance(repo).execute(student_id="s1")
    assert out["evaluations_count"] == 0
    assert out["radar"]["current"] is None and out["overall"] is None
    assert out["overall_delta"] is None and out["last_evaluation_date"] is None


def test_student_performance_wrong_school_raises():
    repo = FakeReporting()
    repo.students["s1"] = StudentRef(id="s1", name="Ana", position=None, school_id="sch1")
    with pytest.raises(q.StudentNotFound):
        q.StudentPerformance(repo).execute(student_id="s1", school_id="OUTRA")


def test_student_performance_missing_raises():
    with pytest.raises(q.StudentNotFound):
        q.StudentPerformance(FakeReporting()).execute(student_id="ghost")


def test_peer_averages_ignores_none_per_axis():
    repo = FakeReporting()
    repo.students["s1"] = StudentRef(id="s1", name="L", position=None, school_id="sch1")
    repo.classes["s1"] = ("Sub-9", "U9")
    repo.class_ids = {"a", "b"}
    repo.category_ids = {"a", "b", "c"}
    repo.latest = {"a": [8, None, 6, 4, 10, 2], "b": [6, 8, 6, 6, 6, 6], "c": [None, None, None, None, None, None]}
    out = q.PeerAverages(repo).execute(student_id="s1", school_id="sch1")
    assert out["class_avg"] == [7.0, 8.0, 6.0, 5.0, 8.0, 4.0]  # axis 1: only b present
    assert out["class_size"] == 2 and out["category_size"] == 3


def test_school_overview_includes_top_scorers():
    repo = FakeReporting()
    repo.overview_data = {"total_students": 12, "total_matches": 3}
    repo.scorers = [{"student_id": "s1", "name": "L", "goals": 5, "assists": 2}]
    out = q.SchoolOverview(repo).execute(school_id="sch1")
    assert out["total_students"] == 12
    assert out["top_scorers"][0]["goals"] == 5


def test_leaderboard_limit_passthrough():
    repo = FakeReporting()
    repo.scorers = [{"student_id": str(i), "name": "x", "goals": i, "assists": 0} for i in range(5)]
    out = q.Leaderboard(repo).execute(school_id="sch1", limit=3)
    assert len(out["top_scorers"]) == 3
