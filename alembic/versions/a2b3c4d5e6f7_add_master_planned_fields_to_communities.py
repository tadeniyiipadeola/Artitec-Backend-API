"""add master planned fields to communities

Revision ID: a2b3c4d5e6f7
Revises: 9f3cf740074b
Create Date: 2025-11-26 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = '9f3cf740074b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add master-planned community tracking fields."""
    # Add development_start_year column to communities table
    op.add_column('communities', sa.Column('development_start_year', sa.Integer(), nullable=True,
                                          comment="Year when development started"))

    # Add is_master_planned column to communities table
    op.add_column('communities', sa.Column('is_master_planned', sa.Boolean(), nullable=True,
                                          server_default='0',
                                          comment="Whether this is a master-planned community"))


def downgrade() -> None:
    """Downgrade schema - remove master-planned community tracking fields."""
    # Remove the added columns
    op.drop_column('communities', 'is_master_planned')
    op.drop_column('communities', 'development_start_year')
