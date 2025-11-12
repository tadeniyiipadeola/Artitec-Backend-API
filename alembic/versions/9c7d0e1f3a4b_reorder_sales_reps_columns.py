"""reorder_sales_reps_columns

Revision ID: 9c7d0e1f3a4b
Revises: 8b6c9d0e2f3a
Create Date: 2025-11-11 22:40:00.000000

Reorder columns in sales_reps table for logical grouping:
1. Keys (id, builder_id, community_id)
2. Identity (first_name, last_name, title)
3. Contact (email, phone)
4. Location (region, office_address)
5. Profile (avatar_url, verified)
6. Timestamps (created_at, updated_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '9c7d0e1f3a4b'
down_revision: Union[str, None] = '8b6c9d0e2f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in sales_reps table for better logical organization.
    NOTE: Must drop and recreate foreign keys to reorder FK columns.
    """
    conn = op.get_bind()

    print("🔄 Reordering sales_reps columns...")

    # Step 1: Drop foreign key constraints (check if exists first)
    result = conn.execute(text("""
        SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = 'appdb' AND TABLE_NAME = 'sales_reps'
        AND REFERENCED_TABLE_NAME IS NOT NULL
    """))
    fk_constraints = [row[0] for row in result]
    for fk_name in fk_constraints:
        conn.execute(text(f"ALTER TABLE sales_reps DROP FOREIGN KEY {fk_name}"))

    # id is first (no change needed)

    # builder_id after id (keep as INT to match builder_profiles.id)
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN builder_id INT NOT NULL AFTER id
    """))

    # community_id after builder_id (keep as INT to match communities.id)
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN community_id INT AFTER builder_id
    """))

    # first_name after community_id
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN first_name VARCHAR(128) NOT NULL AFTER community_id
    """))

    # last_name after first_name
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN last_name VARCHAR(128) NOT NULL AFTER first_name
    """))

    # title after last_name
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN title VARCHAR(128) AFTER last_name
    """))

    # email after title
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN email VARCHAR(255) AFTER title
    """))

    # phone after email
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN phone VARCHAR(64) AFTER email
    """))

    # region after phone
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN region VARCHAR(128) AFTER phone
    """))

    # office_address after region
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN office_address VARCHAR(255) AFTER region
    """))

    # avatar_url after office_address
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN avatar_url VARCHAR(1024) AFTER office_address
    """))

    # verified after avatar_url
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN verified BOOLEAN DEFAULT FALSE AFTER avatar_url
    """))

    # created_at after verified
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER verified
    """))

    # updated_at after created_at
    conn.execute(text("""
        ALTER TABLE sales_reps
        MODIFY COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at
    """))

    # Step 2: Re-add foreign key constraints
    conn.execute(text("""
        ALTER TABLE sales_reps
        ADD CONSTRAINT sales_reps_ibfk_1
        FOREIGN KEY (builder_id) REFERENCES builder_profiles(id) ON DELETE CASCADE
    """))

    conn.execute(text("""
        ALTER TABLE sales_reps
        ADD CONSTRAINT fk_sales_reps_community
        FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE
    """))

    print("✅ sales_reps columns reordered successfully!")


def downgrade() -> None:
    """
    No downgrade needed - column order doesn't affect functionality.
    """
    pass
