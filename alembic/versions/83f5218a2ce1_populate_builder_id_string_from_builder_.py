"""populate builder_id_string from builder_profiles

Revision ID: 83f5218a2ce1
Revises: dceca091ea45
Create Date: 2025-11-27 13:25:38.056569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83f5218a2ce1'
down_revision: Union[str, Sequence[str], None] = 'dceca091ea45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Populate builder_id_string from builder_profiles table
    # This updates all existing properties to have the string builder_id
    op.execute("""
        UPDATE properties p
        INNER JOIN builder_profiles b ON p.builder_id = b.id
        SET p.builder_id_string = b.builder_id
        WHERE p.builder_id_string IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Clear builder_id_string values
    op.execute("""
        UPDATE properties
        SET builder_id_string = NULL
    """)
