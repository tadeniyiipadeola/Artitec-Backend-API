"""add_image_hash_to_media

Revision ID: de008e072fd8
Revises: 9c258a25807e
Create Date: 2025-11-15 02:43:07.309723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de008e072fd8'
down_revision: Union[str, Sequence[str], None] = '9c258a25807e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add image_hash column for duplicate detection."""
    op.add_column('media', sa.Column('image_hash', sa.String(64), nullable=True))
    op.create_index('idx_media_image_hash', 'media', ['image_hash'])


def downgrade() -> None:
    """Downgrade schema - remove image_hash column."""
    op.drop_index('idx_media_image_hash', table_name='media')
    op.drop_column('media', 'image_hash')
