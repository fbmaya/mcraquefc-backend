"""add class period (turno)

Revision ID: 39d2b3f8585f
Revises: ca13c95810b5
Create Date: 2026-07-07 16:52:54.905463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39d2b3f8585f'
down_revision: Union[str, Sequence[str], None] = 'ca13c95810b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('classes', sa.Column('period', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('classes', 'period')
