"""Initial schema migration with all 20 core tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Market Data
    op.create_table(
        "market_data",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("open_time", sa.DateTime(), nullable=False),
        sa.Column("close_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("turnover", sa.Numeric(precision=24, scale=8), nullable=True),
        sa.Column("exchange_timestamp", sa.BigInteger(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timeframe", "open_time", name="uq_market_data_sym_tf_open"),
    )
    op.create_index("idx_market_data_lookup", "market_data", ["symbol", "timeframe", "open_time"])

    # 2. Features
    op.create_table(
        "features",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("feature_name", sa.String(length=64), nullable=False),
        sa.Column("feature_value", sa.Float(), nullable=False),
        sa.Column("feature_version", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timeframe", "timestamp", "feature_name", "feature_version", name="uq_features_sym_tf_ts_feat_ver"),
    )

    # 3. Model Registry
    op.create_table(
        "model_registry",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("model_name", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("hyperparameters", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("artifact_path", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_name", "version", name="uq_model_registry_name_version"),
    )

    # 4. Signals
    op.create_table(
        "signals",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("lifecycle", sa.String(length=20), nullable=False),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_agreement", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("entry_low", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("entry_high", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("take_profit_1", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("take_profit_2", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("take_profit_3", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("risk_reward", sa.Float(), nullable=True),
        sa.Column("market_regime", sa.String(length=32), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Trading Journal
    op.create_table(
        "trading_journal",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("signal_id", sa.String(length=64), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("exit_price", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("take_profit", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("fee_paid", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("pnl_usd", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("pnl_pct", sa.Float(), nullable=True),
        sa.Column("mfe_pct", sa.Float(), nullable=True),
        sa.Column("mae_pct", sa.Float(), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("opened_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. Paper Positions
    op.create_table(
        "paper_positions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("signal_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("current_price", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("qty", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("take_profit_1", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("take_profit_2", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("take_profit_3", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("opened_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("paper_positions")
    op.drop_table("trading_journal")
    op.drop_table("signals")
    op.drop_table("model_registry")
    op.drop_table("features")
    op.drop_table("market_data")
