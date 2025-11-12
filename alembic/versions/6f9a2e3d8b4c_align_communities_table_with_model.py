"""align_communities_table_with_model

Revision ID: 6f9a2e3d8b4c
Revises: 5c8d3a4b9e1f
Create Date: 2025-11-11 22:00:00.000000

Comprehensive migration to align the communities table with the current Model.

Changes:
- Rename: zip_code → postal_code
- Rename: description → about
- Add: public_id, community_dues, tax_rate, monthly_fee, followers, homes, residents, founded_year, member_count, intro_video_url
- Drop: address, website_url (deprecated)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '6f9a2e3d8b4c'
down_revision: Union[str, None] = '5c8d3a4b9e1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Align communities table with the current Model schema.
    """
    conn = op.get_bind()

    # ============================================================
    # STEP 1: Rename zip_code → postal_code
    # ============================================================
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'zip_code'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities CHANGE COLUMN zip_code postal_code VARCHAR(20)"))
        print("✅ Renamed zip_code → postal_code")

    # ============================================================
    # STEP 2: Rename description → about
    # ============================================================
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'description'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities CHANGE COLUMN description about TEXT"))
        print("✅ Renamed description → about")

    # ============================================================
    # STEP 3: Add public_id column (with UUID generation for existing rows)
    # ============================================================
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'public_id'
    """))

    if result.scalar() == 0:
        # Add column as nullable first
        conn.execute(text("ALTER TABLE communities ADD COLUMN public_id VARCHAR(64)"))

        # Generate UUIDs for existing rows
        conn.execute(text("""
            UPDATE communities
            SET public_id = UUID()
            WHERE public_id IS NULL
        """))

        # Make it NOT NULL and UNIQUE
        conn.execute(text("ALTER TABLE communities MODIFY COLUMN public_id VARCHAR(64) NOT NULL"))
        conn.execute(text("CREATE UNIQUE INDEX ix_communities_public_id ON communities(public_id)"))
        print("✅ Added public_id column with UUIDs")

    # ============================================================
    # STEP 4: Add financial fields
    # ============================================================
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'community_dues'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN community_dues VARCHAR(64)"))
        print("✅ Added community_dues")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'tax_rate'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN tax_rate VARCHAR(32)"))
        print("✅ Added tax_rate")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'monthly_fee'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN monthly_fee VARCHAR(64)"))
        print("✅ Added monthly_fee")

    # ============================================================
    # STEP 5: Add statistics fields
    # ============================================================
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'followers'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN followers INT DEFAULT 0"))
        print("✅ Added followers")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'homes'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN homes INT DEFAULT 0"))
        print("✅ Added homes")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'residents'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN residents INT DEFAULT 0"))
        print("✅ Added residents")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'founded_year'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN founded_year INT"))
        print("✅ Added founded_year")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'member_count'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN member_count INT DEFAULT 0"))
        print("✅ Added member_count")

    # ============================================================
    # STEP 6: Add media field
    # ============================================================
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'intro_video_url'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN intro_video_url VARCHAR(1024)"))
        print("✅ Added intro_video_url")

    # ============================================================
    # STEP 7: Drop deprecated columns
    # ============================================================
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'address'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN address"))
        print("✅ Dropped deprecated address column")

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'website_url'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN website_url"))
        print("✅ Dropped deprecated website_url column (replaced by community_website_url)")

    print("✅✅✅ Communities table is now fully aligned with Model!")


def downgrade() -> None:
    """
    Reverse the alignment changes.
    """
    conn = op.get_bind()

    # Reverse order of upgrade

    # Add back deprecated columns
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'website_url'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN website_url VARCHAR(255)"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'address'
    """))

    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE communities ADD COLUMN address VARCHAR(255)"))

    # Drop added columns
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'intro_video_url'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN intro_video_url"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'member_count'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN member_count"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'founded_year'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN founded_year"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'residents'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN residents"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'homes'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN homes"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'followers'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN followers"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'monthly_fee'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN monthly_fee"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'tax_rate'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN tax_rate"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'community_dues'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities DROP COLUMN community_dues"))

    # Drop public_id
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'public_id'
    """))

    if result.scalar() > 0:
        conn.execute(text("DROP INDEX ix_communities_public_id ON communities"))
        conn.execute(text("ALTER TABLE communities DROP COLUMN public_id"))

    # Reverse renames
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'about'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities CHANGE COLUMN about description TEXT"))

    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'postal_code'
    """))

    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE communities CHANGE COLUMN postal_code zip_code VARCHAR(20)"))
