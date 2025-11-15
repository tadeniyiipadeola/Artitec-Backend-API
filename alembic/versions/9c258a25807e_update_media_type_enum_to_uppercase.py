"""update_media_type_enum_to_uppercase

Revision ID: 9c258a25807e
Revises: db20a2a4439e
Create Date: 2025-11-14 14:48:31.448278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c258a25807e'
down_revision: Union[str, Sequence[str], None] = 'db20a2a4439e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - change media_type enum from lowercase to uppercase."""
    # Step 1: Change column to VARCHAR temporarily
    op.execute("ALTER TABLE media MODIFY COLUMN media_type VARCHAR(10) NOT NULL")

    # Step 2: Update values from lowercase to uppercase
    op.execute("UPDATE media SET media_type = 'IMAGE' WHERE media_type = 'image'")
    op.execute("UPDATE media SET media_type = 'VIDEO' WHERE media_type = 'video'")

    # Step 3: Change column back to ENUM with uppercase values
    op.execute("ALTER TABLE media MODIFY COLUMN media_type ENUM('IMAGE', 'VIDEO') NOT NULL")


def downgrade() -> None:
    """Downgrade schema - revert media_type enum back to lowercase."""
    # Step 1: Change column to VARCHAR temporarily
    op.execute("ALTER TABLE media MODIFY COLUMN media_type VARCHAR(10) NOT NULL")

    # Step 2: Update values from uppercase to lowercase
    op.execute("UPDATE media SET media_type = 'image' WHERE media_type = 'IMAGE'")
    op.execute("UPDATE media SET media_type = 'video' WHERE media_type = 'VIDEO'")

    # Step 3: Change column back to ENUM with lowercase values
    op.execute("ALTER TABLE media MODIFY COLUMN media_type ENUM('image', 'video') NOT NULL")
