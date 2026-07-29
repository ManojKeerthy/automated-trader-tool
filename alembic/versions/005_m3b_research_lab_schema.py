"""005_m3b_research_lab_schema

Revision ID: 005_m3b_research_lab_schema
Revises: 004_m3a_screening_schema
Create Date: 2026-07-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_m3b_research_lab_schema'
down_revision: Union[str, None] = '004_m3a_screening_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. strategy_scorecards
    op.create_table(
        'strategy_scorecards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.String(length=100), nullable=False),
        sa.Column('strategy_version', sa.String(length=50), nullable=False),
        sa.Column('overall_rating', sa.String(length=20), nullable=False),
        sa.Column('expectancy_r', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('sharpe_retention_pct', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('max_drawdown_pct', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('walk_forward_consistency_pct', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('stressed_profit_factor', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('dimensions_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 2. walk_forward_results
    op.create_table(
        'walk_forward_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', sa.String(length=100), nullable=False),
        sa.Column('strategy_version', sa.String(length=50), nullable=False),
        sa.Column('configuration_hash', sa.String(length=64), nullable=False),
        sa.Column('window_index', sa.Integer(), nullable=False),
        sa.Column('train_start', sa.Date(), nullable=False),
        sa.Column('train_end', sa.Date(), nullable=False),
        sa.Column('test_start', sa.Date(), nullable=False),
        sa.Column('test_end', sa.Date(), nullable=False),
        sa.Column('train_expectancy_r', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('test_expectancy_r', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('train_sharpe', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('test_sharpe', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('test_trades_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_positive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 3. research_graveyard
    op.create_table(
        'research_graveyard',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', sa.String(length=100), nullable=False),
        sa.Column('strategy_family', sa.String(length=50), nullable=False),
        sa.Column('strategy_version', sa.String(length=50), nullable=False),
        sa.Column('configuration_hash', sa.String(length=64), nullable=False),
        sa.Column('parameters_json', sa.JSON(), nullable=False),
        sa.Column('rejection_reason_code', sa.String(length=50), nullable=False),
        sa.Column('rejection_details', sa.JSON(), nullable=False),
        sa.Column('stage_failed', sa.String(length=30), nullable=False),
        sa.Column('git_commit_hash', sa.String(length=40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('strategy_id', 'configuration_hash', name='uq_graveyard_strategy_config'),
    )


def downgrade() -> None:
    op.drop_table('research_graveyard')
    op.drop_table('walk_forward_results')
    op.drop_table('strategy_scorecards')
