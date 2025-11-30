"""rename_community_ids_to_community_id

Revision ID: 856b7e419241
Revises: 6e638b8042e6
Create Date: 2025-11-30 00:06:24.459542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '856b7e419241'
down_revision: Union[str, Sequence[str], None] = '6e638b8042e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename community_ids column to community_id (singular)
    op.alter_column('builder_profiles', 'community_ids',
                    new_column_name='community_id',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Rename community_id back to community_ids
    op.alter_column('builder_profiles', 'community_id',
                    new_column_name='community_ids',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)
