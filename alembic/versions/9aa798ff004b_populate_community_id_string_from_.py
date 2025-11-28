"""populate community_id_string from communities

Revision ID: 9aa798ff004b
Revises: 1e32247d8f53
Create Date: 2025-11-27 13:17:06.992543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9aa798ff004b'
down_revision: Union[str, Sequence[str], None] = '1e32247d8f53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Populate community_id_string from communities table
    # This updates all existing properties to have the string community_id
    op.execute("""
        UPDATE properties p
        INNER JOIN communities c ON p.community_id = c.id
        SET p.community_id_string = c.community_id
        WHERE p.community_id_string IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Clear community_id_string values
    op.execute("""
        UPDATE properties
        SET community_id_string = NULL
    """)
