"""split_community_admin_display_name_into_first_last

Revision ID: 5c8d3a4b9e1f
Revises: 4b8712726b4d
Create Date: 2025-11-11 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '5c8d3a4b9e1f'
down_revision: Union[str, None] = '4b8712726b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Split display_name into first_name and last_name in community_admin_profiles table.
    Similar to the sales_reps migration.
    """
    conn = op.get_bind()

    # Check if display_name column exists
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admin_profiles'
        AND COLUMN_NAME = 'display_name'
    """))

    if result.scalar() > 0:
        # Step 1: Add first_name and last_name columns (nullable first)
        conn.execute(text("ALTER TABLE community_admin_profiles ADD COLUMN first_name VARCHAR(128)"))
        conn.execute(text("ALTER TABLE community_admin_profiles ADD COLUMN last_name VARCHAR(128)"))

        # Step 2: Split existing display_name data
        # If display_name contains a space, split on first space
        # Otherwise, put entire name in first_name
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

        # Step 3: Make columns NOT NULL
        conn.execute(text("ALTER TABLE community_admin_profiles MODIFY COLUMN first_name VARCHAR(128) NOT NULL"))
        conn.execute(text("ALTER TABLE community_admin_profiles MODIFY COLUMN last_name VARCHAR(128) NOT NULL"))

        # Step 4: Drop old display_name column
        conn.execute(text("ALTER TABLE community_admin_profiles DROP COLUMN display_name"))


def downgrade() -> None:
    """
    Reverse the split: combine first_name and last_name back into display_name.
    """
    conn = op.get_bind()

    # Check if first_name and last_name columns exist
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admin_profiles'
        AND COLUMN_NAME IN ('first_name', 'last_name')
    """))

    if result.scalar() == 2:
        # Step 1: Add display_name column
        conn.execute(text("ALTER TABLE community_admin_profiles ADD COLUMN display_name VARCHAR(255)"))

        # Step 2: Combine first_name and last_name
        conn.execute(text("""
            UPDATE community_admin_profiles
            SET display_name = CONCAT(first_name, ' ', last_name)
        """))

        # Step 3: Drop first_name and last_name columns
        conn.execute(text("ALTER TABLE community_admin_profiles DROP COLUMN first_name"))
        conn.execute(text("ALTER TABLE community_admin_profiles DROP COLUMN last_name"))
