"""family fase 1 — tabela family_subscriptions (assinatura individual)

Revision ID: c8e2f3a4b5d6
Revises: b7d1e2f3a4c5
Create Date: 2026-07-11 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e2f3a4b5d6'
down_revision: Union[str, Sequence[str], None] = 'b7d1e2f3a4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'family_subscriptions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('parent_id', sa.String(length=36), nullable=False),
        sa.Column('school_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.Enum('active', 'overdue', 'cancelled', 'pending', name='familysubstatus'), nullable=False),
        sa.Column('price_tier', sa.Enum('cheio', 'pontualidade', 'promo', name='familypricetier'), nullable=False),
        sa.Column('current_period', sa.Date(), nullable=True),
        sa.Column('expires_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['users.id']),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_family_subscriptions_parent_id', 'family_subscriptions', ['parent_id'])
    op.create_index('ix_family_subscriptions_school_id', 'family_subscriptions', ['school_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_family_subscriptions_school_id', table_name='family_subscriptions')
    op.drop_index('ix_family_subscriptions_parent_id', table_name='family_subscriptions')
    op.drop_table('family_subscriptions')
    sa.Enum(name='familypricetier').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='familysubstatus').drop(op.get_bind(), checkfirst=True)
