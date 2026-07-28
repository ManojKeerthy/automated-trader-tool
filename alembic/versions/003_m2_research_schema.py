"""M2 research schema

Revision ID: 003_m2_research_schema
Revises: 002_add_transformation_version
Create Date: 2026-07-28 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '003_m2_research_schema'
down_revision: Union[str, None] = '002_add_transformation_version'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add sector and industry to instruments
    op.add_column('instruments', sa.Column('sector', sa.String(length=100), nullable=True))
    op.add_column('instruments', sa.Column('industry', sa.String(length=100), nullable=True))

    # 2. Create instrument_history table
    op.create_table(
        'instrument_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('old_symbol', sa.String(length=50), nullable=True),
        sa.Column('new_symbol', sa.String(length=50), nullable=True),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=False, server_default='UNVERIFIED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 3. Create universe_membership table
    op.create_table(
        'universe_membership',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('index_name', sa.String(length=50), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('verified_as_of', sa.Date(), nullable=True),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence', sa.String(length=20), nullable=False, server_default='UNVERIFIED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 4. Create strategy_definitions table
    op.create_table(
        'strategy_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('module_path', sa.String(length=255), nullable=True),
        sa.Column('lifecycle_stage', sa.String(length=50), nullable=False, server_default='IDEA'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('promoted_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_strategy_name_version'),
    )

    # 5. Create experiments table
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy_name', sa.String(length=100), nullable=True),
        sa.Column('strategy_version', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='CREATED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # 6. Create cost_schedules table
    op.create_table(
        'cost_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('exchange', sa.String(length=10), nullable=False, server_default='NSE'),
        sa.Column('segment', sa.String(length=20), nullable=False, server_default='EQ_DELIVERY'),
        sa.Column('schedule_json', postgresql.JSONB(), nullable=False),
        sa.Column('source_references', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version', 'exchange', 'segment', name='uq_cost_schedule_version'),
    )

    # 7. Create backtest_runs table
    op.create_table(
        'backtest_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('strategy_name', sa.String(length=100), nullable=False),
        sa.Column('strategy_version', sa.String(length=50), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('universe', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('initial_capital', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cost_model_version', sa.String(length=50), nullable=False),
        sa.Column('slippage_model', sa.String(length=100), nullable=False),
        sa.Column('benchmark', sa.String(length=100), nullable=True),
        sa.Column('risk_free_rate', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('risk_free_rate_source', sa.String(length=200), nullable=True),
        sa.Column('risk_free_rate_observation_date', sa.Date(), nullable=True),
        sa.Column('risk_free_rate_type', sa.String(length=50), nullable=False,
                  server_default='CURRENT_RATE_ASSUMPTION'),
        sa.Column('data_version', sa.String(length=100), nullable=True),
        sa.Column('calendar_version', sa.String(length=50), nullable=True),
        sa.Column('research_quality', sa.String(length=30), nullable=False,
                  server_default='UNVERIFIED'),
        sa.Column('warnings', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='RUNNING'),
        sa.Column('run_timestamp', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 8. Create backtest_trades table
    op.create_table(
        'backtest_trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_symbol', sa.String(length=50), nullable=False),
        sa.Column('strategy_name', sa.String(length=100), nullable=False),
        sa.Column('strategy_version', sa.String(length=50), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('signal_date', sa.Date(), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=True),
        sa.Column('entry_price', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('exit_date', sa.Date(), nullable=True),
        sa.Column('exit_price', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('gross_pnl', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('total_fees', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('slippage_cost', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('net_pnl', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('holding_days', sa.Integer(), nullable=True),
        sa.Column('exit_reason', sa.String(length=100), nullable=True),
        sa.Column('fees_breakdown', postgresql.JSONB(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 9. Create backtest_metrics table
    op.create_table(
        'backtest_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('metric_status', sa.String(length=30), nullable=True),
        sa.Column('metric_metadata', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'metric_name', name='uq_run_metric'),
    )


def downgrade() -> None:
    op.drop_table('backtest_metrics')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_runs')
    op.drop_table('cost_schedules')
    op.drop_table('experiments')
    op.drop_table('strategy_definitions')
    op.drop_table('universe_membership')
    op.drop_table('instrument_history')
    op.drop_column('instruments', 'industry')
    op.drop_column('instruments', 'sector')
