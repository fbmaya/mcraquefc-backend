"""family fase 1 — dados base (Student.active, License.family_included/price)

Revision ID: b7d1e2f3a4c5
Revises: 39d2b3f8585f
Create Date: 2026-07-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d1e2f3a4c5'
down_revision: Union[str, Sequence[str], None] = '39d2b3f8585f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Aluno ativo por padrão; backfill dos existentes via server_default.
    op.add_column('students', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    # Family incluso no plano School (default: não incluso) + preço/aluno quando incluso.
    op.add_column('licenses', sa.Column('family_included', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('licenses', sa.Column('family_price_per_student', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('licenses', 'family_price_per_student')
    op.drop_column('licenses', 'family_included')
    op.drop_column('students', 'active')
