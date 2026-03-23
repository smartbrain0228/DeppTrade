"""add signal event history

Revision ID: 20260312_0002
Revises: 20260305_0001
Create Date: 2026-03-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260312_0002"
down_revision = "20260305_0001"
branch_labels = None
depends_on = None


signal_trigger_enum = sa.Enum("SCAN", "EXECUTE", name="signal_trigger_enum", native_enum=False)
signal_status_enum = sa.Enum(
    "NO_BIAS",
    "WAITING_SWEEP",
    "WAITING_MSS",
    "WAITING_FVG",
    "READY",
    name="signal_status_enum",
    native_enum=False,
)
signal_side_enum = sa.Enum("BUY", "SELL", name="signal_side_enum", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "signal_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("trade_id", sa.BigInteger(), nullable=True),
        sa.Column("trigger", signal_trigger_enum, nullable=False),
        sa.Column("signal_status", signal_status_enum, nullable=False),
        sa.Column("signal_reason", sa.String(length=255), nullable=False),
        sa.Column("side", signal_side_enum, nullable=True),
        sa.Column("htf_bias", sa.String(length=20), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["assignment_id"], ["user_pair_strategies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_signal_events_assignment_id", "signal_events", ["assignment_id"], unique=False)
    op.create_index("ix_signal_events_user_id", "signal_events", ["user_id"], unique=False)
    op.create_index("ix_signal_events_symbol_id", "signal_events", ["symbol_id"], unique=False)
    op.create_index("ix_signal_events_strategy_id", "signal_events", ["strategy_id"], unique=False)
    op.create_index("ix_signal_events_trade_id", "signal_events", ["trade_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_signal_events_trade_id", table_name="signal_events")
    op.drop_index("ix_signal_events_strategy_id", table_name="signal_events")
    op.drop_index("ix_signal_events_symbol_id", table_name="signal_events")
    op.drop_index("ix_signal_events_user_id", table_name="signal_events")
    op.drop_index("ix_signal_events_assignment_id", table_name="signal_events")
    op.drop_table("signal_events")
