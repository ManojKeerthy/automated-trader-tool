"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-28 16:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create instruments table
    op.create_table(
        'instruments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('isin', sa.String(length=20), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('exchange', sa.String(length=10), nullable=False),
        sa.Column('segment', sa.String(length=20), nullable=False),
        sa.Column('tick_size', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('lot_size', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('instrument_token', sa.Integer(), nullable=True),
        sa.Column('nifty50_member_from', sa.Date(), nullable=True),
        sa.Column('nifty50_member_to', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exchange', 'symbol', name='uq_exchange_symbol')
    )

    # 2. Create market_bars table
    op.create_table(
        'market_bars',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trading_date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('high', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('low', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('close', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_adjusted', sa.Boolean(), nullable=False),
        sa.Column('adjustment_factor', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'trading_date', 'is_adjusted', name='uq_instrument_date_adj')
    )

    # 3. Create corporate_actions table
    op.create_table(
        'corporate_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('ex_date', sa.Date(), nullable=False),
        sa.Column('record_date', sa.Date(), nullable=True),
        sa.Column('ratio_from', sa.Integer(), nullable=True),
        sa.Column('ratio_to', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instrument_id', 'action_type', 'ex_date', name='uq_instrument_action_date')
    )


def downgrade() -> None:
    op.drop_table('corporate_actions')
    op.drop_table('market_bars')
    op.drop_table('instruments')
