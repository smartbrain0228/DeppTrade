"""expand strategy name enum

Revision ID: 69cdb0164f73
Revises: 20260312_0002
Create Date: 2026-03-15 17:14:53.634773
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '69cdb0164f73'
down_revision = '20260312_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update strategies.name
    op.alter_column('strategies', 'name',
               existing_type=sa.VARCHAR(length=8),
               type_=sa.String(length=30),
               existing_nullable=False)
    
    # 2. Update trades.tag
    op.alter_column('trades', 'tag',
               existing_type=sa.VARCHAR(length=8),
               type_=sa.String(length=30),
               existing_nullable=False)
    
    # 3. Update signal_events.analysis (JSON) - not needed but good to check others
    # UserPairStrategy has strategy_id, so it's fine.


def downgrade() -> None:
    op.alter_column('trades', 'tag',
               existing_type=sa.String(length=30),
               type_=sa.VARCHAR(length=8),
               existing_nullable=False)
    
    op.alter_column('strategies', 'name',
               existing_type=sa.String(length=30),
               type_=sa.VARCHAR(length=8),
               existing_nullable=False)
