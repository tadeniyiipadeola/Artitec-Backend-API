"""add user_id to communities

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2025-11-12 22:00:00.000000

Add user_id FK to communities table to track community owner/creator
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, None] = 'f2g3h4i5j6k7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id FK to communities table."""
    print("\n🔧 Adding user_id to communities table...")

    conn = op.get_bind()

    # Check if user_id column already exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'user_id'
    """))

    column_exists = result.scalar() > 0

    if not column_exists:
        # Add user_id column (nullable initially)
        # Use Integer to match users.id type (not BIGINT)
        op.add_column(
            'communities',
            sa.Column('user_id', sa.Integer(), nullable=True)
        )
        print("   ✓ Added user_id column")
    else:
        print("   ℹ user_id column already exists")
        # Check and fix the column type if needed
        result = conn.execute(text("""
            SELECT DATA_TYPE, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'communities'
            AND COLUMN_NAME = 'user_id'
        """))
        col_info = result.fetchone()
        if col_info and 'bigint' in col_info[1].lower():
            print("   ⚠ Column type is BIGINT, converting to INT to match users.id...")
            conn.execute(text("ALTER TABLE communities MODIFY COLUMN user_id INT"))
            print("   ✓ Column type fixed")

    # Check if FK constraint already exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'user_id'
        AND CONSTRAINT_NAME = 'fk_communities_user_id'
    """))

    fk_exists = result.scalar() > 0

    if not fk_exists:
        # Add foreign key constraint
        op.create_foreign_key(
            'fk_communities_user_id',
            'communities',
            'users',
            ['user_id'],
            ['id'],
            ondelete='SET NULL'  # If user deleted, don't delete community
        )
        print("   ✓ Added FK constraint to users.id")
    else:
        print("   ℹ FK constraint already exists")

    # Check if index already exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND INDEX_NAME = 'ix_communities_user_id'
    """))

    index_exists = result.scalar() > 0

    if not index_exists:
        # Add index for faster lookups
        op.create_index('ix_communities_user_id', 'communities', ['user_id'])
        print("   ✓ Added index ix_communities_user_id")
    else:
        print("   ℹ Index already exists")

    print("✅ Migration completed successfully")
    print("   - Column: user_id (INTEGER)")
    print("   - FK: users.id")
    print("   - Index: ix_communities_user_id")
    print("   - Nullable: Yes (existing communities won't break)")


def downgrade() -> None:
    """Remove user_id from communities table."""
    print("\n⚠️  Removing user_id from communities table...")

    # Drop index
    op.drop_index('ix_communities_user_id', table_name='communities')

    # Drop foreign key
    op.drop_constraint('fk_communities_user_id', 'communities', type_='foreignkey')

    # Drop column
    op.drop_column('communities', 'user_id')

    print("✅ Removed user_id column from communities table")
