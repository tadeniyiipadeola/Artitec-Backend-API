"""create community_admin_profiles table

Revision ID: c0d1e2f3g4h5
Revises: b2c3d4e5f6g7
Create Date: 2025-11-12 00:00:00.000000

Creates the community_admin_profiles table for linking users to communities they administer.
Similar to buyer_profiles and builder_profiles pattern.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'c0d1e2f3g4h5'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'  # After followers table
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create community_admin_profiles table"""

    # Check if table already exists
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admin_profiles'
    """))

    if result.scalar() > 0:
        print("Table community_admin_profiles already exists, skipping creation")
        return

    # Create the table
    op.create_table(
        'community_admin_profiles',

        # Primary Key
        # FIXED: Changed from Integer to BIGINT(unsigned) to match other profile tables
        sa.Column('id', mysql.BIGINT(unsigned=True), nullable=False, autoincrement=True),

        # One-to-one with users.id (unique)
        # FIXED: Changed from Integer to BIGINT(unsigned) to match users.id type
        sa.Column('user_id', mysql.BIGINT(unsigned=True), nullable=False),

        # Links to the community this admin manages
        # FIXED: Changed from Integer to BIGINT(unsigned) to match communities.id type
        sa.Column('community_id', mysql.BIGINT(unsigned=True), nullable=False),

        # Profile/Display (will be split into first_name/last_name in later migration)
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('profile_image', sa.String(500), nullable=True),
        sa.Column('bio', sa.Text, nullable=True),
        sa.Column('title', sa.String(128), nullable=True),

        # Contact
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(64), nullable=True),
        sa.Column('contact_preferred', sa.String(32), nullable=True),

        # Permissions
        sa.Column('can_post_announcements', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('can_manage_events', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('can_moderate_threads', sa.Boolean, nullable=False, server_default='1'),

        # Metadata
        sa.Column('extra', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', mysql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', mysql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_community_admin_user'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_community_admin_user', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], name='fk_community_admin_community', ondelete='CASCADE'),

        # Table properties
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='Profiles for users who are community administrators'
    )

    # Create indexes
    op.create_index('idx_community_admin_user_id', 'community_admin_profiles', ['user_id'])
    op.create_index('idx_community_admin_community_id', 'community_admin_profiles', ['community_id'])

    print("✓ Created community_admin_profiles table")


def downgrade() -> None:
    """Drop community_admin_profiles table"""

    # Drop indexes first
    op.drop_index('idx_community_admin_community_id', table_name='community_admin_profiles')
    op.drop_index('idx_community_admin_user_id', table_name='community_admin_profiles')

    # Drop table
    op.drop_table('community_admin_profiles')

    print("✓ Dropped community_admin_profiles table")
