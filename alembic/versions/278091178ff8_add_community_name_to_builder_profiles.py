"""add_community_name_to_builder_profiles

Revision ID: 278091178ff8
Revises: b60420daff97
Create Date: 2025-11-29 22:25:01.489779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '278091178ff8'
down_revision: Union[str, Sequence[str], None] = 'b60420daff97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add community_name column to builder_profiles table
    op.add_column('builder_profiles', sa.Column('community_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove community_name column from builder_profiles table
    op.drop_column('builder_profiles', 'community_name')
