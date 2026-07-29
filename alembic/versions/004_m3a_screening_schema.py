"""M3A screening schema

Revision ID: 004_m3a_screening_schema
Revises: 003_m2_research_schema
Create Date: 2026-07-29 01:30:00.000000

Creates tables for:
- feature_definitions: Versioned feature metadata for reproducibility
- market_regime_snapshots: Point-in-time regime classifications
- screening_runs: Screening run metadata and audit trail
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '004_m3a_screening_schema'
down_revision: Union[str, None] = '003_m2_research_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type() -> sa.types.TypeEngine:
    """Return JSONB on PostgreSQL, JSON on other dialects."""
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # --- feature_definitions ---
    op.create_table(
        'feature_definitions',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('family', sa.String(50), nullable=False),
        sa.Column('parameters', _json_type(), nullable=True),
        sa.Column('required_lookback', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('input_series', _json_type(), nullable=True),
        sa.Column('availability', sa.String(30), nullable=False, server_default='IMMEDIATE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_feature_name_version'),
    )

    # --- market_regime_snapshots ---
    op.create_table(
        'market_regime_snapshots',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('observation_date', sa.Date(), nullable=False),
        sa.Column('regime_version', sa.String(50), nullable=False),
        sa.Column('trend', sa.String(20), nullable=False),
        sa.Column('volatility', sa.String(20), nullable=False),
        sa.Column('breadth', sa.String(20), nullable=False),
        sa.Column('trend_quality', sa.String(30), nullable=False, server_default='COMPUTED'),
        sa.Column('volatility_quality', sa.String(30), nullable=False, server_default='COMPUTED'),
        sa.Column('breadth_quality', sa.String(30), nullable=False, server_default='COMPUTED'),
        sa.Column('overall_quality', sa.String(30), nullable=False, server_default='COMPUTED'),
        sa.Column('metrics_json', _json_type(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('observation_date', 'regime_version', name='uq_regime_date_version'),
    )

    # --- screening_runs ---
    op.create_table(
        'screening_runs',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('screen_date', sa.Date(), nullable=False),
        sa.Column('screening_version', sa.String(50), nullable=False),
        sa.Column('eligibility_config_version', sa.String(50), nullable=False),
        sa.Column('liquidity_config_version', sa.String(50), nullable=False),
        sa.Column('regime_definition_version', sa.String(50), nullable=False),
        sa.Column('total_universe', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('eligible_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('excluded_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('candidate_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('regime_trend', sa.String(20), nullable=True),
        sa.Column('regime_volatility', sa.String(20), nullable=True),
        sa.Column('regime_breadth', sa.String(20), nullable=True),
        sa.Column('regime_overall_quality', sa.String(30), nullable=True),
        sa.Column('exclusion_summary', _json_type(), nullable=True),
        sa.Column('research_quality_warnings', _json_type(), nullable=True),
        sa.Column('feature_versions', _json_type(), nullable=True),
        sa.Column('execution_metadata', _json_type(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('screening_runs')
    op.drop_table('market_regime_snapshots')
    op.drop_table('feature_definitions')
