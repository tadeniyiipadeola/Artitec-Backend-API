"""add public_ids to all profiles

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3g4h5i6
Create Date: 2025-11-12 14:00:00.000000

Adds public_id columns to all profile tables using the format PREFIX-TIMESTAMP-RANDOM
- BuyerProfile: BYR-1699564234-A7K9M2
- BuilderProfile: BLD-1699564234-X3P8Q1 (renames build_id to public_id)
- CommunityAdminProfile: ADM-1699564234-M2K9L3
- SalesRep: SLS-1699564234-P7Q8R9
- Community: Already has public_id, will backfill to new format
- Users: Backfill to new format USR-1699564234-A7K9M2
"""
from typing import Sequence, Union
import sys
import os

# Add parent directory to path to import id_generator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import text

# Import our ID generator
from src.id_generator import (
    generate_user_id,
    generate_buyer_id,
    generate_builder_id,
    generate_community_admin_id,
    generate_sales_rep_id,
    generate_community_id,
)

# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, None] = 'd1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add public_id columns to all profile tables and backfill with typed IDs."""
    conn = op.get_bind()

    print("\n🔧 Starting public_id migration...")

    # =========================================================================
    # 1. USERS TABLE - Backfill existing public_ids to new format
    # =========================================================================
    print("\n1️⃣  Updating users.public_id to new format (USR-TIMESTAMP-RANDOM)...")

    users = conn.execute(text("SELECT id, public_id FROM users"))
    user_count = 0
    for row in users:
        new_public_id = generate_user_id()
        conn.execute(
            text("UPDATE users SET public_id = :new_id WHERE id = :id"),
            {"new_id": new_public_id, "id": row.id}
        )
        user_count += 1

    print(f"   ✅ Updated {user_count} user public_ids")

    # =========================================================================
    # 2. BUYER_PROFILES TABLE - Add public_id column
    # =========================================================================
    print("\n2️⃣  Adding public_id to buyer_profiles...")

    # Check if column exists
    has_public_id = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'buyer_profiles'
        AND COLUMN_NAME = 'public_id'
    """)).scalar() > 0

    if not has_public_id:
        # Add column (nullable initially for backfill)
        op.add_column(
            'buyer_profiles',
            sa.Column('public_id', sa.String(50), nullable=True, unique=True)
        )

    # Backfill existing buyer profiles (only those without public_id)
    buyers = conn.execute(text("SELECT id FROM buyer_profiles WHERE public_id IS NULL"))
    buyer_count = 0
    for row in buyers:
        new_public_id = generate_buyer_id()
        conn.execute(
            text("UPDATE buyer_profiles SET public_id = :pid WHERE id = :id"),
            {"pid": new_public_id, "id": row.id}
        )
        buyer_count += 1

    if not has_public_id or buyer_count > 0:
        # Make NOT NULL and add index
        op.alter_column('buyer_profiles', 'public_id', existing_type=sa.String(50), nullable=False)

        # Check if index exists before creating
        has_index = conn.execute(text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'buyer_profiles'
            AND INDEX_NAME = 'ix_buyer_profiles_public_id'
        """)).scalar() > 0

        if not has_index:
            op.create_index('ix_buyer_profiles_public_id', 'buyer_profiles', ['public_id'], unique=True)

    print(f"   ✅ Added public_id to {buyer_count} buyer profiles")

    # =========================================================================
    # 3. BUILDER_PROFILES TABLE - Rename build_id to public_id and update format
    # =========================================================================
    print("\n3️⃣  Updating builder_profiles.build_id to public_id with new format...")

    # Add new public_id column
    op.add_column(
        'builder_profiles',
        sa.Column('public_id', sa.String(50), nullable=True, unique=True)
    )

    # Backfill all builders with new format
    builders = conn.execute(text("SELECT id, build_id FROM builder_profiles"))
    builder_count = 0
    for row in builders:
        new_public_id = generate_builder_id()
        conn.execute(
            text("UPDATE builder_profiles SET public_id = :pid WHERE id = :id"),
            {"pid": new_public_id, "id": row.id}
        )
        builder_count += 1

    # Make NOT NULL and add index
    op.alter_column('builder_profiles', 'public_id', existing_type=sa.String(50), nullable=False)
    op.create_index('ix_builder_profiles_public_id', 'builder_profiles', ['public_id'], unique=True)

    # Drop old build_id column (after data migration)
    op.drop_column('builder_profiles', 'build_id')

    print(f"   ✅ Migrated {builder_count} builder profiles from build_id to public_id")

    # =========================================================================
    # 4. COMMUNITY_ADMIN_PROFILES TABLE - Add public_id column
    # =========================================================================
    print("\n4️⃣  Adding public_id to community_admin_profiles...")

    # Check if table exists
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admin_profiles'
    """))

    if result.scalar() > 0:
        # Add column
        op.add_column(
            'community_admin_profiles',
            sa.Column('public_id', sa.String(50), nullable=True, unique=True)
        )

        # Backfill existing community admin profiles
        admins = conn.execute(text("SELECT id FROM community_admin_profiles"))
        admin_count = 0
        for row in admins:
            new_public_id = generate_community_admin_id()
            conn.execute(
                text("UPDATE community_admin_profiles SET public_id = :pid WHERE id = :id"),
                {"pid": new_public_id, "id": row.id}
            )
            admin_count += 1

        # Make NOT NULL and add index
        if admin_count > 0:
            op.alter_column('community_admin_profiles', 'public_id', existing_type=sa.String(50), nullable=False)
        op.create_index('ix_community_admin_profiles_public_id', 'community_admin_profiles', ['public_id'], unique=True)

        print(f"   ✅ Added public_id to {admin_count} community admin profiles")
    else:
        print("   ⚠️  Table community_admin_profiles does not exist, skipping")

    # =========================================================================
    # 5. SALES_REPS TABLE - Add public_id column
    # =========================================================================
    print("\n5️⃣  Adding public_id to sales_reps...")

    # Add column
    op.add_column(
        'sales_reps',
        sa.Column('public_id', sa.String(50), nullable=True, unique=True)
    )

    # Backfill existing sales reps
    sales_reps = conn.execute(text("SELECT id FROM sales_reps"))
    rep_count = 0
    for row in sales_reps:
        new_public_id = generate_sales_rep_id()
        conn.execute(
            text("UPDATE sales_reps SET public_id = :pid WHERE id = :id"),
            {"pid": new_public_id, "id": row.id}
        )
        rep_count += 1

    # Make NOT NULL and add index
    if rep_count > 0:
        op.alter_column('sales_reps', 'public_id', existing_type=sa.String(50), nullable=False)
    op.create_index('ix_sales_reps_public_id', 'sales_reps', ['public_id'], unique=True)

    print(f"   ✅ Added public_id to {rep_count} sales reps")

    # =========================================================================
    # 6. COMMUNITIES TABLE - Backfill to new format
    # =========================================================================
    print("\n6️⃣  Updating communities.public_id to new format (CMY-TIMESTAMP-RANDOM)...")

    communities = conn.execute(text("SELECT id, public_id FROM communities"))
    community_count = 0
    for row in communities:
        new_public_id = generate_community_id()
        conn.execute(
            text("UPDATE communities SET public_id = :new_id WHERE id = :id"),
            {"new_id": new_public_id, "id": row.id}
        )
        community_count += 1

    print(f"   ✅ Updated {community_count} community public_ids")

    print("\n✨ Migration complete! All profiles now have typed public_ids\n")


def downgrade() -> None:
    """Remove public_id columns and restore old format."""
    print("\n⚠️  Rolling back public_id migration...")

    # Sales reps
    op.drop_index('ix_sales_reps_public_id', table_name='sales_reps')
    op.drop_column('sales_reps', 'public_id')

    # Community admin profiles
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admin_profiles'
    """))

    if result.scalar() > 0:
        op.drop_index('ix_community_admin_profiles_public_id', table_name='community_admin_profiles')
        op.drop_column('community_admin_profiles', 'public_id')

    # Builder profiles - restore build_id
    op.add_column('builder_profiles', sa.Column('build_id', sa.String(64), nullable=True))
    op.drop_index('ix_builder_profiles_public_id', table_name='builder_profiles')
    op.drop_column('builder_profiles', 'public_id')

    # Buyer profiles
    op.drop_index('ix_buyer_profiles_public_id', table_name='buyer_profiles')
    op.drop_column('buyer_profiles', 'public_id')

    print("✅ Rollback complete")
