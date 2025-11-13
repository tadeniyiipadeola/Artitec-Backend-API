"""add_user_id_to_sales_reps

Revision ID: 396dd510e408
Revises: 43f361179508
Create Date: 2025-11-12 22:38:11.971577

Add user_id FK column to sales_reps table to link sales reps to user accounts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '396dd510e408'
down_revision: Union[str, Sequence[str], None] = '43f361179508'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id FK to sales_reps table."""
    print("\n🔧 Adding user_id to sales_reps table...")

    conn = op.get_bind()

    # Check if user_id column already exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'sales_reps'
        AND COLUMN_NAME = 'user_id'
    """))

    column_exists = result.scalar() > 0

    if not column_exists:
        # Add user_id column (nullable) - using Integer to match users.id type
        op.add_column(
            'sales_reps',
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
            AND TABLE_NAME = 'sales_reps'
            AND COLUMN_NAME = 'user_id'
        """))
        col_info = result.fetchone()
        if col_info and 'bigint' in col_info[1].lower():
            print("   ⚠ Column type is BIGINT, converting to INT to match users.id...")
            conn.execute(text("ALTER TABLE sales_reps MODIFY COLUMN user_id INT"))
            print("   ✓ Column type fixed")

    # Check if FK constraint already exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'sales_reps'
        AND COLUMN_NAME = 'user_id'
        AND CONSTRAINT_NAME = 'fk_sales_reps_user_id'
    """))

    fk_exists = result.scalar() > 0

    if not fk_exists:
        # Add foreign key constraint
        op.create_foreign_key(
            'fk_sales_reps_user_id',
            'sales_reps',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )
        print("   ✓ Added FK constraint to users.id")
    else:
        print("   ℹ FK constraint already exists")

    # Check if index already exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'sales_reps'
        AND INDEX_NAME = 'ix_sales_reps_user_id'
    """))

    index_exists = result.scalar() > 0

    if not index_exists:
        # Add index for faster lookups
        op.create_index('ix_sales_reps_user_id', 'sales_reps', ['user_id'])
        print("   ✓ Added index ix_sales_reps_user_id")
    else:
        print("   ℹ Index already exists")

    print("✅ Migration completed successfully")
    print("   - Column: user_id (BIGINT UNSIGNED)")
    print("   - FK: users.id")
    print("   - Index: ix_sales_reps_user_id")
    print("   - Nullable: Yes (existing sales reps won't break)")


def downgrade() -> None:
    """Remove user_id from sales_reps table."""
    print("\n⚠️  Removing user_id from sales_reps table...")

    # Drop index
    op.drop_index('ix_sales_reps_user_id', table_name='sales_reps')

    # Drop foreign key
    op.drop_constraint('fk_sales_reps_user_id', 'sales_reps', type_='foreignkey')

    # Drop column
    op.drop_column('sales_reps', 'user_id')

    print("✅ Removed user_id column from sales_reps table")
