"""índices nas FKs quentes (school_id / student_id / joins)

Revision ID: e5b6c7d8f9a0
Revises: d9a1b2c3e4f5
Create Date: 2026-07-11 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5b6c7d8f9a0'
down_revision: Union[str, Sequence[str], None] = 'd9a1b2c3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (nome_do_indice, tabela, coluna) — FKs usadas em WHERE/JOIN nos repositórios.
_INDEXES = [
    ("ix_students_school_id", "students", "school_id"),
    ("ix_users_school_id", "users", "school_id"),
    ("ix_classes_school_id", "classes", "school_id"),
    ("ix_class_enrollments_class_id", "class_enrollments", "class_id"),
    ("ix_class_enrollments_student_id", "class_enrollments", "student_id"),
    ("ix_payments_student_id", "payments", "student_id"),
    ("ix_evaluations_student_id", "evaluations", "student_id"),
    ("ix_attendance_sessions_class_id", "attendance_sessions", "class_id"),
    ("ix_attendance_records_session_id", "attendance_records", "session_id"),
    ("ix_attendance_records_student_id", "attendance_records", "student_id"),
    ("ix_matches_school_id", "matches", "school_id"),
    ("ix_match_stats_match_id", "match_stats", "match_id"),
    ("ix_match_stats_student_id", "match_stats", "student_id"),
    ("ix_parent_student_links_parent_id", "parent_student_links", "parent_id"),
    ("ix_parent_student_links_student_id", "parent_student_links", "student_id"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for name, table, column in _INDEXES:
        op.create_index(name, table, [column])


def downgrade() -> None:
    """Downgrade schema."""
    for name, table, _ in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
