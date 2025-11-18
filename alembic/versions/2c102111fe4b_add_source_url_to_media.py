"""add_source_url_to_media

Revision ID: 2c102111fe4b
Revises: 8f4f0cbc28a2
Create Date: 2025-11-15 11:50:19.446556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c102111fe4b'
down_revision: Union[str, Sequence[str], None] = '8f4f0cbc28a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source_url column to media table for tracking where media was scraped from."""
    op.add_column('media', sa.Column('source_url', sa.Text(), nullable=True, comment='Source URL if scraped from a website'))


def downgrade() -> None:
    """Remove source_url column from media table."""
    op.drop_column('media', 'source_url')
