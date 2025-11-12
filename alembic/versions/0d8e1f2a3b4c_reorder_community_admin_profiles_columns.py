"""reorder_community_admin_profiles_columns

Revision ID: 0d8e1f2a3b4c
Revises: 9c7d0e1f3a4b
Create Date: 2025-11-11 22:45:00.000000

Reorder columns in community_admin_profiles table for logical grouping:
1. Keys (id, user_id, community_id)
2. Identity (first_name, last_name, title)
3. Contact (contact_email, contact_phone, contact_preferred)
4. Profile (profile_image, bio)
5. Permissions (can_post_announcements, can_manage_events, can_moderate_threads)
6. Additional (extra)
7. Timestamps (created_at, updated_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0d8e1f2a3b4c'
down_revision: Union[str, None] = '9c7d0e1f3a4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in community_admin_profiles table for better logical organization.
    NOTE: Must drop and recreate foreign keys to reorder FK columns.
    """
    conn = op.get_bind()

    print("🔄 Reordering community_admin_profiles columns...")

    # Check if table exists
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'appdb' AND TABLE_NAME = 'community_admin_profiles'
    """))
    table_exists = result.scalar() > 0

    if not table_exists:
        print("⏭️  Table community_admin_profiles doesn't exist yet, skipping reorder")
        return

    # Step 1: Drop foreign key constraints (check if exists first)
    result = conn.execute(text("""
        SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = 'appdb' AND TABLE_NAME = 'community_admin_profiles'
        AND REFERENCED_TABLE_NAME IS NOT NULL
    """))
    fk_constraints = [row[0] for row in result]
    for fk_name in fk_constraints:
        conn.execute(text(f"ALTER TABLE community_admin_profiles DROP FOREIGN KEY {fk_name}"))

    # id is first (no change needed)

    # user_id after id (keep as INT to match users.id)
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN user_id INT NOT NULL AFTER id
    """))

    # community_id after user_id (keep as INT to match communities.id)
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN community_id INT NOT NULL AFTER user_id
    """))

    # first_name after community_id
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN first_name VARCHAR(128) NOT NULL AFTER community_id
    """))

    # last_name after first_name
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN last_name VARCHAR(128) NOT NULL AFTER first_name
    """))

    # title after last_name
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN title VARCHAR(128) AFTER last_name
    """))

    # contact_email after title
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN contact_email VARCHAR(255) AFTER title
    """))

    # contact_phone after contact_email
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN contact_phone VARCHAR(64) AFTER contact_email
    """))

    # contact_preferred after contact_phone
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN contact_preferred VARCHAR(32) AFTER contact_phone
    """))

    # profile_image after contact_preferred
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN profile_image VARCHAR(500) AFTER contact_preferred
    """))

    # bio after profile_image
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN bio TEXT AFTER profile_image
    """))

    # can_post_announcements after bio
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN can_post_announcements BOOLEAN NOT NULL DEFAULT TRUE AFTER bio
    """))

    # can_manage_events after can_post_announcements
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN can_manage_events BOOLEAN NOT NULL DEFAULT TRUE AFTER can_post_announcements
    """))

    # can_moderate_threads after can_manage_events
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN can_moderate_threads BOOLEAN NOT NULL DEFAULT TRUE AFTER can_manage_events
    """))

    # extra after can_moderate_threads
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN extra TEXT AFTER can_moderate_threads
    """))

    # created_at after extra
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER extra
    """))

    # updated_at after created_at
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        MODIFY COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at
    """))

    # Step 2: Re-add foreign key constraints
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        ADD CONSTRAINT community_admin_profiles_ibfk_1
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """))

    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        ADD CONSTRAINT community_admin_profiles_ibfk_2
        FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE
    """))

    print("✅ community_admin_profiles columns reordered successfully!")


def downgrade() -> None:
    """
    No downgrade needed - column order doesn't affect functionality.
    """
    pass
