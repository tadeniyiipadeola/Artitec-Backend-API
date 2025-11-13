"""create followers table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-12 12:05:00.000000

Creates the followers table to track user-to-user following relationships.
This enables social features like following buyers, builders, sales reps, etc.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create followers table for tracking follow relationships."""
    op.create_table(
        'followers',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        # FIXED: Changed from Integer to BIGINT(unsigned) to match users.id type
        sa.Column('follower_user_id', mysql.BIGINT(unsigned=True), nullable=False, comment='User who is following'),
        sa.Column('following_user_id', mysql.BIGINT(unsigned=True), nullable=False, comment='User being followed'),
        sa.Column('created_at', mysql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(
            ['follower_user_id'],
            ['users.id'],
            name='fk_followers_follower_user',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['following_user_id'],
            ['users.id'],
            name='fk_followers_following_user',
            ondelete='CASCADE'
        ),

        # Unique constraint - a user can only follow another user once
        sa.UniqueConstraint(
            'follower_user_id',
            'following_user_id',
            name='uq_follower_following'
        ),

        # Check constraint - users cannot follow themselves
        sa.CheckConstraint(
            'follower_user_id != following_user_id',
            name='ck_no_self_follow'
        ),

        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # Create indexes for efficient queries
    op.create_index(
        'ix_followers_follower_user_id',
        'followers',
        ['follower_user_id'],
        unique=False
    )

    op.create_index(
        'ix_followers_following_user_id',
        'followers',
        ['following_user_id'],
        unique=False
    )

    # NOTE: Composite index removed - the unique constraint on (follower_user_id, following_user_id)
    # automatically creates an index, so a separate composite index is redundant


def downgrade() -> None:
    """Drop the followers table."""
    # Drop indexes first
    op.drop_index('ix_followers_following_user_id', table_name='followers')
    op.drop_index('ix_followers_follower_user_id', table_name='followers')

    # Drop the table
    op.drop_table('followers')
