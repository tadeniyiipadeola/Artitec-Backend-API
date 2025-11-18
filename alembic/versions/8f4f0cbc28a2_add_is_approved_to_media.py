"""add_is_approved_to_media

Revision ID: 8f4f0cbc28a2
Revises: de008e072fd8
Create Date: 2025-11-15 11:11:36.480910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f4f0cbc28a2'
down_revision: Union[str, Sequence[str], None] = 'de008e072fd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_approved column for auto-cleanup of unused scraped media."""
    # Add is_approved column, default to True for existing media (keep them)
    op.add_column('media', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='1'))

    # Create index for efficient cleanup queries
    op.create_index('idx_media_is_approved_created_at', 'media', ['is_approved', 'created_at'])


def downgrade() -> None:
    """Remove is_approved column."""
    op.drop_index('idx_media_is_approved_created_at', table_name='media')
    op.drop_column('media', 'is_approved')
