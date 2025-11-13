"""replace role_id with role key

Revision ID: f2g3h4i5j6k7
Revises: e1f2g3h4i5j6
Create Date: 2025-11-12 16:00:00.000000

Replaces users.role_id (integer FK) with users.role (string/enum).
More readable, simpler queries, better API responses.

Before: user.role_id = 1 → roles.key = "buyer"
After:  user.role = "buyer"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'f2g3h4i5j6k7'
down_revision: Union[str, None] = 'e1f2g3h4i5j6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace role_id with role (string/enum)."""
    conn = op.get_bind()

    print("\n🔧 Replacing users.role_id with users.role...")

    # =========================================================================
    # Step 1: Add new 'role' column (nullable for now)
    # =========================================================================
    print("\n1️⃣  Adding users.role column...")

    # Option A: Use VARCHAR (more flexible)
    op.add_column(
        'users',
        sa.Column('role', sa.String(32), nullable=True)
    )

    # Option B: Use ENUM (stricter, uncomment if preferred)
    # op.execute("""
    #     ALTER TABLE users
    #     ADD COLUMN role ENUM('buyer', 'builder', 'community', 'community_admin', 'salesrep', 'admin')
    #     NULL
    # """)

    print("   ✅ Added users.role column")

    # =========================================================================
    # Step 2: Backfill role values from roles table
    # =========================================================================
    print("\n2️⃣  Backfilling users.role from roles.key...")

    # Get all users with their role keys
    result = conn.execute(text("""
        SELECT u.id, u.role_id, r.key
        FROM users u
        JOIN roles r ON u.role_id = r.id
    """))

    user_count = 0
    role_distribution = {}

    for row in result:
        # Update user's role to the role key
        conn.execute(
            text("UPDATE users SET role = :role WHERE id = :id"),
            {"role": row.key, "id": row.id}
        )
        user_count += 1

        # Track distribution
        role_distribution[row.key] = role_distribution.get(row.key, 0) + 1

    print(f"   ✅ Updated {user_count} users:")
    for role, count in sorted(role_distribution.items()):
        print(f"      - {role}: {count} users")

    # =========================================================================
    # Step 3: Make role NOT NULL and add index
    # =========================================================================
    print("\n3️⃣  Making users.role required and indexed...")

    # Make NOT NULL
    op.alter_column('users', 'role', existing_type=sa.String(32), nullable=False)

    # Add index for faster queries
    op.create_index('ix_users_role', 'users', ['role'], unique=False)

    print("   ✅ Added NOT NULL constraint and index")

    # =========================================================================
    # Step 4: Drop old role_id column and foreign key
    # =========================================================================
    print("\n4️⃣  Removing old role_id column...")

    # Drop foreign key constraint first
    # Note: Constraint name may vary, check with SHOW CREATE TABLE users
    try:
        op.drop_constraint('users_ibfk_1', 'users', type_='foreignkey')
    except Exception:
        # Try alternate constraint name
        try:
            op.drop_constraint('fk_users_role', 'users', type_='foreignkey')
        except Exception as e:
            print(f"   ⚠️  Could not drop FK constraint: {e}")
            print("   ℹ️  You may need to drop it manually")

    # Drop the column
    op.drop_column('users', 'role_id')

    print("   ✅ Removed role_id column")

    # =========================================================================
    # Step 5: Keep roles table as reference (optional)
    # =========================================================================
    print("\n5️⃣  Keeping roles table for reference...")
    print("   ℹ️  Roles table can be used for:")
    print("      - Display names (Buyer, Builder, etc.)")
    print("      - Descriptions")
    print("      - UI metadata (icons, colors)")
    print("      - Permission mappings")

    print("\n✨ Migration complete! users.role now uses direct role keys\n")


def downgrade() -> None:
    """Restore role_id from role."""
    conn = op.get_bind()

    print("\n⚠️  Rolling back to role_id...")

    # Add role_id column back
    op.add_column(
        'users',
        sa.Column('role_id', sa.SmallInteger(), nullable=True)
    )

    # Populate role_id from role key
    result = conn.execute(text("""
        SELECT u.id, u.role, r.id as role_id
        FROM users u
        JOIN roles r ON u.role = r.key
    """))

    for row in result:
        conn.execute(
            text("UPDATE users SET role_id = :role_id WHERE id = :id"),
            {"role_id": row.role_id, "id": row.id}
        )

    # Make NOT NULL
    op.alter_column('users', 'role_id', existing_type=sa.SmallInteger(), nullable=False)

    # Restore foreign key
    op.create_foreign_key(
        'users_ibfk_1',
        'users', 'roles',
        ['role_id'], ['id'],
        ondelete='RESTRICT'
    )

    # Drop role column and index
    op.drop_index('ix_users_role', table_name='users')
    op.drop_column('users', 'role')

    print("✅ Rolled back to role_id")
