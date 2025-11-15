"""increase_media_public_id_length

Revision ID: dfdb0998c3c5
Revises: h4i5j6k7l8m9
Create Date: 2025-11-14 14:25:57.582615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfdb0998c3c5'
down_revision: Union[str, Sequence[str], None] = 'h4i5j6k7l8m9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Increase public_id column length from VARCHAR(20) to VARCHAR(30)
    # to accommodate media IDs like "MED-1763151795-W0OGYL" (22 chars)
    op.alter_column('media', 'public_id',
                    existing_type=sa.String(20),
                    type_=sa.String(30),
                    existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert public_id column back to VARCHAR(20)
    op.alter_column('media', 'public_id',
                    existing_type=sa.String(30),
                    type_=sa.String(20),
                    existing_nullable=False)
