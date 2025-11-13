"""add followers_count to buyer_profiles

Revision ID: a1b2c3d4e5f6
Revises: 9c7d0e1f3a4b
Create Date: 2025-11-12 12:00:00.000000

Adds followers_count column to buyer_profiles table to track social engagement.
This is a denormalized counter that will be updated when follow/unfollow actions occur.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '1e9f2a3b4c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add followers_count column to buyer_profiles table."""
    # Add followers_count column with default value of 0
    op.add_column(
        'buyer_profiles',
        sa.Column('followers_count', sa.Integer(), nullable=False, server_default='0')
    )

    # Create index for efficient queries when displaying top buyers by followers
    op.create_index(
        'ix_buyer_profiles_followers_count',
        'buyer_profiles',
        ['followers_count'],
        unique=False
    )


def downgrade() -> None:
    """Remove followers_count column from buyer_profiles table."""
    # Drop the index first
    op.drop_index('ix_buyer_profiles_followers_count', table_name='buyer_profiles')

    # Remove the column
    op.drop_column('buyer_profiles', 'followers_count')
