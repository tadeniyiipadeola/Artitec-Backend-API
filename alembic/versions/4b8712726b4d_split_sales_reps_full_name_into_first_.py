"""split sales_reps full_name into first_name and last_name

Revision ID: 4b8712726b4d
Revises: 2ab2d90ffbc5
Create Date: 2025-11-11 21:12:40.790528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '4b8712726b4d'
down_revision: Union[str, Sequence[str], None] = '2ab2d90ffbc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Split full_name into first_name and last_name in sales_reps table."""
    conn = op.get_bind()

    # Check if full_name column exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'sales_reps'
        AND COLUMN_NAME = 'full_name'
    """))

    if result.scalar() > 0:
        # Add first_name and last_name columns
        conn.execute(text("ALTER TABLE sales_reps ADD COLUMN first_name VARCHAR(128)"))
        conn.execute(text("ALTER TABLE sales_reps ADD COLUMN last_name VARCHAR(128)"))

        # Split existing full_name data (if any rows exist)
        # This is a simple split on first space - assumes "FirstName LastName" format
        conn.execute(text("""
            UPDATE sales_reps
            SET first_name = SUBSTRING_INDEX(full_name, ' ', 1),
                last_name = SUBSTRING_INDEX(full_name, ' ', -1)
            WHERE full_name IS NOT NULL
        """))

        # Make columns NOT NULL after data migration
        conn.execute(text("ALTER TABLE sales_reps MODIFY COLUMN first_name VARCHAR(128) NOT NULL"))
        conn.execute(text("ALTER TABLE sales_reps MODIFY COLUMN last_name VARCHAR(128) NOT NULL"))

        # Drop the old full_name column
        conn.execute(text("ALTER TABLE sales_reps DROP COLUMN full_name"))
    else:
        # full_name doesn't exist, just add first_name and last_name if they don't exist
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'sales_reps'
            AND COLUMN_NAME = 'first_name'
        """))
        if result.scalar() == 0:
            conn.execute(text("ALTER TABLE sales_reps ADD COLUMN first_name VARCHAR(128) NOT NULL"))

        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'sales_reps'
            AND COLUMN_NAME = 'last_name'
        """))
        if result.scalar() == 0:
            conn.execute(text("ALTER TABLE sales_reps ADD COLUMN last_name VARCHAR(128) NOT NULL"))


def downgrade() -> None:
    """Merge first_name and last_name back into full_name."""
    conn = op.get_bind()

    # Check if first_name and last_name exist
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'sales_reps'
        AND COLUMN_NAME IN ('first_name', 'last_name')
    """))

    if result.scalar() >= 2:
        # Add full_name column
        conn.execute(text("ALTER TABLE sales_reps ADD COLUMN full_name VARCHAR(255)"))

        # Merge first_name and last_name back into full_name
        conn.execute(text("""
            UPDATE sales_reps
            SET full_name = CONCAT(first_name, ' ', last_name)
            WHERE first_name IS NOT NULL AND last_name IS NOT NULL
        """))

        # Make full_name NOT NULL
        conn.execute(text("ALTER TABLE sales_reps MODIFY COLUMN full_name VARCHAR(255) NOT NULL"))

        # Drop first_name and last_name
        conn.execute(text("ALTER TABLE sales_reps DROP COLUMN first_name"))
        conn.execute(text("ALTER TABLE sales_reps DROP COLUMN last_name"))
