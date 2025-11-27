"""add lot_number to properties table

Revision ID: 6f51a9c242b0
Revises: e5bff7628465
Create Date: 2025-11-27 06:27:29.505280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f51a9c242b0'
down_revision: Union[str, Sequence[str], None] = 'e5bff7628465'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('properties', sa.Column('lot_number', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('properties', 'lot_number')
