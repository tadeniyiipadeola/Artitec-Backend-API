"""add community_id_string to properties table

Revision ID: 1e32247d8f53
Revises: 6f51a9c242b0
Create Date: 2025-11-27 13:11:49.868888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e32247d8f53'
down_revision: Union[str, Sequence[str], None] = '6f51a9c242b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('properties', sa.Column('community_id_string', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('properties', 'community_id_string')
