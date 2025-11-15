"""increase_media_uploaded_by_length

Revision ID: db20a2a4439e
Revises: dfdb0998c3c5
Create Date: 2025-11-14 14:29:04.866101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db20a2a4439e'
down_revision: Union[str, Sequence[str], None] = 'dfdb0998c3c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Increase uploaded_by column length from VARCHAR(20) to VARCHAR(30)
    # to accommodate user IDs like "USR-1763002155-GRZVLL" (23 chars)
    op.alter_column('media', 'uploaded_by',
                    existing_type=sa.String(20),
                    type_=sa.String(30),
                    existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert uploaded_by column back to VARCHAR(20)
    op.alter_column('media', 'uploaded_by',
                    existing_type=sa.String(30),
                    type_=sa.String(20),
                    existing_nullable=False)
