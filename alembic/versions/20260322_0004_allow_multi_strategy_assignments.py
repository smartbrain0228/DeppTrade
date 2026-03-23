"""allow multiple strategies per user and symbol

Revision ID: 20260322_0004
Revises: 20260320_0003
Create Date: 2026-03-22 12:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260322_0004"
down_revision = "20260320_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_user_symbol_strategy", "user_pair_strategies", type_="unique")
    op.create_unique_constraint(
        "uq_user_symbol_strategy",
        "user_pair_strategies",
        ["user_id", "symbol_id", "strategy_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_symbol_strategy", "user_pair_strategies", type_="unique")
    op.create_unique_constraint(
        "uq_user_symbol_strategy",
        "user_pair_strategies",
        ["user_id", "symbol_id"],
    )
