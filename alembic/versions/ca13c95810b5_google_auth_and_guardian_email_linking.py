"""google auth and guardian email linking

Revision ID: ca13c95810b5
Revises: e99385d55a33
Create Date: 2026-07-06 23:11:20.666900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca13c95810b5'
down_revision: Union[str, Sequence[str], None] = 'e99385d55a33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # students: vínculo por email do responsável substitui o access_code
    op.add_column('students', sa.Column('guardian_email', sa.String(length=200), nullable=True))
    op.create_index(op.f('ix_students_guardian_email'), 'students', ['guardian_email'], unique=False)
    op.drop_index(op.f('ix_students_access_code'), table_name='students')
    op.drop_column('students', 'access_code')

    # users: suporte a login com Google (sem senha local)
    op.add_column('users', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_google_sub'), 'users', ['google_sub'], unique=True)
    op.alter_column('users', 'hashed_password', existing_type=sa.String(length=200), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'hashed_password', existing_type=sa.String(length=200), nullable=False)
    op.drop_index(op.f('ix_users_google_sub'), table_name='users')
    op.drop_column('users', 'google_sub')

    op.add_column('students', sa.Column('access_code', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_students_access_code'), 'students', ['access_code'], unique=True)
    op.drop_index(op.f('ix_students_guardian_email'), table_name='students')
    op.drop_column('students', 'guardian_email')
