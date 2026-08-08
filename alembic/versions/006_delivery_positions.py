"""006_delivery_positions

Revision ID: 006_delivery_positions
Revises: 005_m3b_research_lab_schema
Create Date: 2026-08-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_delivery_positions"
down_revision: str | None = "005_m3b_research_lab_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "instrument_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("instruments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("traded_qty", sa.BigInteger(), nullable=False),
        sa.Column("delivery_qty", sa.BigInteger(), nullable=False),
        sa.Column("delivery_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="NSE_MTO"),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("instrument_id", "trading_date", name="uq_instrument_delivery_date"),
    )
    op.create_index(
        "ix_delivery_positions_instrument_date",
        "delivery_positions",
        ["instrument_id", "trading_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_positions_instrument_date", table_name="delivery_positions")
    op.drop_table("delivery_positions")
