"""initial schema

Revision ID: 20260305_0001
Revises: None
Create Date: 2026-03-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0001"
down_revision = None
branch_labels = None
depends_on = None


role_enum = sa.Enum("ADMIN", "TRADER", "VIEWER", name="role_enum", native_enum=False)
strategy_name_enum = sa.Enum(
    "INTRADAY", "SCALP", name="strategy_name_enum", native_enum=False
)
trade_tag_enum = sa.Enum("INTRADAY", "SCALP", name="trade_tag_enum", native_enum=False)
trade_side_enum = sa.Enum("BUY", "SELL", name="trade_side_enum", native_enum=False)
trade_status_enum = sa.Enum(
    "PENDING", "OPEN", "CLOSED", "CANCELED", name="trade_status_enum", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="TRADER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", strategy_name_enum, nullable=False),
        sa.Column("htf", sa.String(length=10), nullable=False),
        sa.Column("ltf", sa.String(length=10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("name", name="uq_strategies_name"),
    )

    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("base_asset", sa.String(length=20), nullable=False),
        sa.Column(
            "quote_asset",
            sa.String(length=20),
            nullable=False,
            server_default="USDT",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("exchange", "symbol", name="uq_symbol_exchange"),
    )
    op.create_index("ix_symbols_exchange", "symbols", ["exchange"], unique=False)
    op.create_index("ix_symbols_symbol", "symbols", ["symbol"], unique=False)

    op.create_table(
        "user_pair_strategies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("risk_pct", sa.Numeric(precision=5, scale=2), nullable=False, server_default="1.00"),
        sa.Column("max_trades_per_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "symbol_id", name="uq_user_symbol_strategy"),
    )
    op.create_index(
        "ix_user_pair_strategies_user_id", "user_pair_strategies", ["user_id"], unique=False
    )
    op.create_index(
        "ix_user_pair_strategies_symbol_id",
        "user_pair_strategies",
        ["symbol_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_pair_strategies_strategy_id",
        "user_pair_strategies",
        ["strategy_id"],
        unique=False,
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("tag", trade_tag_enum, nullable=False),
        sa.Column("side", trade_side_enum, nullable=False),
        sa.Column(
            "status",
            trade_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("entry_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("take_profit", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=28, scale=10), nullable=False),
        sa.Column("pnl", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_trades_user_id", "trades", ["user_id"], unique=False)
    op.create_index("ix_trades_symbol_id", "trades", ["symbol_id"], unique=False)
    op.create_index("ix_trades_strategy_id", "trades", ["strategy_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_trades_strategy_id", table_name="trades")
    op.drop_index("ix_trades_symbol_id", table_name="trades")
    op.drop_index("ix_trades_user_id", table_name="trades")
    op.drop_table("trades")

    op.drop_index("ix_user_pair_strategies_strategy_id", table_name="user_pair_strategies")
    op.drop_index("ix_user_pair_strategies_symbol_id", table_name="user_pair_strategies")
    op.drop_index("ix_user_pair_strategies_user_id", table_name="user_pair_strategies")
    op.drop_table("user_pair_strategies")

    op.drop_index("ix_symbols_symbol", table_name="symbols")
    op.drop_index("ix_symbols_exchange", table_name="symbols")
    op.drop_table("symbols")

    op.drop_table("strategies")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
