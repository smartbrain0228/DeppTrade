"""align multi-strategy schema with current models

Revision ID: 20260320_0003
Revises: 6d744a77c42f
Create Date: 2026-03-20 00:03:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260320_0003"
down_revision = "6d744a77c42f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_pair_strategies",
        sa.Column(
            "demo_balance",
            sa.Numeric(precision=20, scale=8),
            nullable=False,
            server_default="100.0",
        ),
    )
    op.add_column(
        "user_pair_strategies",
        sa.Column("trade_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_pair_strategies",
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.add_column("trades", sa.Column("spot_bias", sa.String(length=20), nullable=True))
    op.add_column("trades", sa.Column("futures_bias", sa.String(length=20), nullable=True))
    op.add_column(
        "trades",
        sa.Column("has_divergence", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("trades", sa.Column("skip_reason", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("trades", "skip_reason")
    op.drop_column("trades", "has_divergence")
    op.drop_column("trades", "futures_bias")
    op.drop_column("trades", "spot_bias")

    op.drop_column("user_pair_strategies", "is_paused")
    op.drop_column("user_pair_strategies", "trade_count")
    op.drop_column("user_pair_strategies", "demo_balance")
