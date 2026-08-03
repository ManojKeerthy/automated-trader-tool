"""add transformation_version

Revision ID: 002_add_transformation_version
Revises: 001_initial_schema
Create Date: 2026-07-28 17:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_add_transformation_version'
down_revision: str | None = '001_initial_schema'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('market_bars', sa.Column('transformation_version', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('market_bars', 'transformation_version')
