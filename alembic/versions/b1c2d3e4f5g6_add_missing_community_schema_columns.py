"""add missing community schema columns

Revision ID: b1c2d3e4f5g6
Revises: c0d1e2f3g4h5
Create Date: 2025-11-12 15:00:00.000000

Adds all missing columns and tables needed for The Highlands seed data:
- Add is_verified, development_stage, enterprise_number_hoa, community_website_url to communities
- Add gallery column to community_amenities
- Create community_builders table
- Create community_admins table
- Create community_awards table
- Create community_topics table
- Update community_phases to match model (lots as JSON, map_url)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = 'c0d1e2f3g4h5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing community schema columns and tables"""

    conn = op.get_bind()

    print("=" * 70)
    print("Adding missing community schema columns and tables...")
    print("=" * 70)

    # ========================================================================
    # STEP 1: Add missing columns to communities table
    # ========================================================================
    print("\nStep 1: Adding missing columns to communities table...")

    # Add is_verified column
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'is_verified'
    """))

    if result.scalar() == 0:
        conn.execute(text("""
            ALTER TABLE communities
            ADD COLUMN is_verified BOOLEAN DEFAULT 0 AFTER about
        """))
        print("✓ Added is_verified column")
    else:
        print("  is_verified column already exists")

    # Add development_stage column
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'development_stage'
    """))

    if result.scalar() == 0:
        conn.execute(text("""
            ALTER TABLE communities
            ADD COLUMN development_stage VARCHAR(64) AFTER member_count
        """))
        print("✓ Added development_stage column")
    else:
        print("  development_stage column already exists")

    # Add enterprise_number_hoa column
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'enterprise_number_hoa'
    """))

    if result.scalar() == 0:
        conn.execute(text("""
            ALTER TABLE communities
            ADD COLUMN enterprise_number_hoa VARCHAR(255) AFTER development_stage
        """))
        print("✓ Added enterprise_number_hoa column")
    else:
        print("  enterprise_number_hoa column already exists")

    # Add community_website_url column
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'community_website_url'
    """))

    if result.scalar() == 0:
        conn.execute(text("""
            ALTER TABLE communities
            ADD COLUMN community_website_url VARCHAR(1024) AFTER intro_video_url
        """))
        print("✓ Added community_website_url column")
    else:
        print("  community_website_url column already exists")

    # ========================================================================
    # STEP 2: Add gallery column to community_amenities
    # ========================================================================
    print("\nStep 2: Adding gallery column to community_amenities...")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_amenities'
        AND COLUMN_NAME = 'gallery'
    """))

    if result.scalar() == 0:
        conn.execute(text("""
            ALTER TABLE community_amenities
            ADD COLUMN gallery JSON AFTER name
        """))
        print("✓ Added gallery column")
    else:
        print("  gallery column already exists")

    # ========================================================================
    # STEP 3: Create community_builders table
    # ========================================================================
    print("\nStep 3: Creating community_builders table...")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_builders'
    """))

    if result.scalar() == 0:
        op.create_table(
            'community_builders',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('community_id', sa.Integer(), sa.ForeignKey('communities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('icon', sa.String(64)),
            sa.Column('name', sa.String(255)),
            sa.Column('subtitle', sa.String(255)),
            sa.Column('followers', sa.Integer(), server_default='0'),
            sa.Column('is_verified', sa.Boolean(), server_default='0'),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4',
            mysql_collate='utf8mb4_unicode_ci'
        )
        op.create_index('idx_community_builders_community_id', 'community_builders', ['community_id'])
        print("✓ Created community_builders table")
    else:
        print("  community_builders table already exists")

    # ========================================================================
    # STEP 4: Create community_admins table
    # ========================================================================
    print("\nStep 4: Creating community_admins table...")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admins'
    """))

    if result.scalar() == 0:
        op.create_table(
            'community_admins',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('community_id', sa.Integer(), sa.ForeignKey('communities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(255)),
            sa.Column('role', sa.String(128)),
            sa.Column('email', sa.String(255)),
            sa.Column('phone', sa.String(64)),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4',
            mysql_collate='utf8mb4_unicode_ci'
        )
        op.create_index('idx_community_admins_community_id', 'community_admins', ['community_id'])
        print("✓ Created community_admins table")
    else:
        print("  community_admins table already exists")

    # ========================================================================
    # STEP 5: Create community_awards table
    # ========================================================================
    print("\nStep 5: Creating community_awards table...")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_awards'
    """))

    if result.scalar() == 0:
        op.create_table(
            'community_awards',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('community_id', sa.Integer(), sa.ForeignKey('communities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('title', sa.String(255)),
            sa.Column('year', sa.Integer()),
            sa.Column('issuer', sa.String(255)),
            sa.Column('icon', sa.String(64)),
            sa.Column('note', sa.Text()),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4',
            mysql_collate='utf8mb4_unicode_ci'
        )
        op.create_index('idx_community_awards_community_id', 'community_awards', ['community_id'])
        print("✓ Created community_awards table")
    else:
        print("  community_awards table already exists")

    # ========================================================================
    # STEP 6: Create community_topics table
    # ========================================================================
    print("\nStep 6: Creating community_topics table...")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_topics'
    """))

    if result.scalar() == 0:
        op.create_table(
            'community_topics',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('community_id', sa.Integer(), sa.ForeignKey('communities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('title', sa.String(255)),
            sa.Column('category', sa.String(255)),
            sa.Column('replies', sa.Integer(), server_default='0'),
            sa.Column('last_activity', sa.String(128)),
            sa.Column('is_pinned', sa.Boolean(), server_default='0'),
            sa.Column('comments', sa.JSON()),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4',
            mysql_collate='utf8mb4_unicode_ci'
        )
        op.create_index('idx_community_topics_community_id', 'community_topics', ['community_id'])
        print("✓ Created community_topics table")
    else:
        print("  community_topics table already exists")

    # ========================================================================
    # STEP 7: Split display_name into first_name and last_name in community_admin_profiles
    # ========================================================================
    print("\nStep 7: Splitting display_name in community_admin_profiles...")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admin_profiles'
        AND COLUMN_NAME = 'display_name'
    """))

    if result.scalar() > 0:
        # Add first_name and last_name columns
        conn.execute(text("ALTER TABLE community_admin_profiles ADD COLUMN first_name VARCHAR(128)"))
        conn.execute(text("ALTER TABLE community_admin_profiles ADD COLUMN last_name VARCHAR(128)"))

        # Split existing display_name data
        conn.execute(text("""
            UPDATE community_admin_profiles
            SET first_name = CASE
                WHEN display_name LIKE '% %' THEN SUBSTRING_INDEX(display_name, ' ', 1)
                ELSE display_name
            END,
            last_name = CASE
                WHEN display_name LIKE '% %' THEN SUBSTRING_INDEX(display_name, ' ', -1)
                ELSE ''
            END
            WHERE display_name IS NOT NULL
        """))

        # Set default values for rows with NULL display_name
        conn.execute(text("""
            UPDATE community_admin_profiles
            SET first_name = 'Unknown',
                last_name = 'Admin'
            WHERE display_name IS NULL
        """))

        # Make columns NOT NULL
        conn.execute(text("ALTER TABLE community_admin_profiles MODIFY COLUMN first_name VARCHAR(128) NOT NULL"))
        conn.execute(text("ALTER TABLE community_admin_profiles MODIFY COLUMN last_name VARCHAR(128) NOT NULL"))

        # Drop old display_name column
        conn.execute(text("ALTER TABLE community_admin_profiles DROP COLUMN display_name"))
        print("✓ Split display_name into first_name and last_name")
    else:
        print("  display_name column does not exist, skipping split")

    # ========================================================================
    # STEP 8: Update community_phases table to match model
    # ========================================================================
    print("\nStep 8: Updating community_phases table to match model...")

    # Add lots column as JSON if it doesn't exist
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'lots'
    """))

    if result.scalar() == 0:
        conn.execute(text("""
            ALTER TABLE community_phases
            ADD COLUMN lots JSON AFTER name
        """))
        print("✓ Added lots column to community_phases")
    else:
        print("  lots column already exists in community_phases")

    # Add map_url column if it doesn't exist
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'map_url'
    """))

    if result.scalar() == 0:
        conn.execute(text("""
            ALTER TABLE community_phases
            ADD COLUMN map_url VARCHAR(1024) AFTER lots
        """))
        print("✓ Added map_url column to community_phases")
    else:
        print("  map_url column already exists in community_phases")

    # Drop old columns that are no longer in the model (phase_number, status)
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'phase_number'
    """))

    if result.scalar() > 0:
        conn.execute(text("""
            ALTER TABLE community_phases
            DROP COLUMN phase_number
        """))
        print("✓ Removed phase_number column from community_phases")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'status'
    """))

    if result.scalar() > 0:
        conn.execute(text("""
            ALTER TABLE community_phases
            DROP COLUMN status
        """))
        print("✓ Removed status column from community_phases")

    print("\n" + "=" * 70)
    print("✅ All missing community schema columns and tables added successfully!")
    print("=" * 70)


def downgrade() -> None:
    """Remove added community schema columns and tables"""

    conn = op.get_bind()

    print("Removing added community schema columns and tables...")

    # Drop community_topics table
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_topics'
    """))

    if result.scalar() > 0:
        op.drop_index('idx_community_topics_community_id', table_name='community_topics')
        op.drop_table('community_topics')
        print("✓ Dropped community_topics table")

    # Drop community_awards table
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_awards'
    """))

    if result.scalar() > 0:
        op.drop_index('idx_community_awards_community_id', table_name='community_awards')
        op.drop_table('community_awards')
        print("✓ Dropped community_awards table")

    # Drop community_admins table
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admins'
    """))

    if result.scalar() > 0:
        op.drop_index('idx_community_admins_community_id', table_name='community_admins')
        op.drop_table('community_admins')
        print("✓ Dropped community_admins table")

    # Drop community_builders table
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_builders'
    """))

    if result.scalar() > 0:
        op.drop_index('idx_community_builders_community_id', table_name='community_builders')
        op.drop_table('community_builders')
        print("✓ Dropped community_builders table")

    # Remove gallery column from community_amenities
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_amenities'
        AND COLUMN_NAME = 'gallery'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE community_amenities DROP COLUMN gallery"))
        print("✓ Removed gallery column from community_amenities")

    # Remove columns from communities table
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'community_website_url'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN community_website_url"))
        print("✓ Removed community_website_url column from communities")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'enterprise_number_hoa'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN enterprise_number_hoa"))
        print("✓ Removed enterprise_number_hoa column from communities")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'development_stage'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN development_stage"))
        print("✓ Removed development_stage column from communities")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'is_verified'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN is_verified"))
        print("✓ Removed is_verified column from communities")

    # Restore old community_phases columns
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'map_url'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE community_phases DROP COLUMN map_url"))
        print("✓ Removed map_url column from community_phases")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'lots'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE community_phases DROP COLUMN lots"))
        print("✓ Removed lots column from community_phases")

    # Add back old columns
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'phase_number'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE community_phases ADD COLUMN phase_number INT AFTER name"))
        print("✓ Restored phase_number column to community_phases")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_phases'
        AND COLUMN_NAME = 'status'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE community_phases ADD COLUMN status VARCHAR(64) AFTER phase_number"))
        print("✓ Restored status column to community_phases")

    print("✓ Removed all added community schema columns and tables")
