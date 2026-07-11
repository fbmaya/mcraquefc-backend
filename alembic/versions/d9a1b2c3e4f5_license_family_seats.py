"""family fase 1 — License.family_seats (cota contratada, cap flexível)

Revision ID: d9a1b2c3e4f5
Revises: c8e2f3a4b5d6
Create Date: 2026-07-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9a1b2c3e4f5'
down_revision: Union[str, Sequence[str], None] = 'c8e2f3a4b5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('licenses', sa.Column('family_seats', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('licenses', 'family_seats')
