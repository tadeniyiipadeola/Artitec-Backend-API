"""fix_community_admin_profiles_user_id

Revision ID: bc3b0a6a067f
Revises: e1393a7f6239
Create Date: 2025-11-12 22:42:45.347136

Complete the conversion of community_admin_profiles.user_id from INTEGER to VARCHAR(50).
This handles the case where the previous migration partially completed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'bc3b0a6a067f'
down_revision: Union[str, Sequence[str], None] = 'e1393a7f6239'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix community_admin_profiles.user_id conversion."""
    print("\n🔧 Fixing community_admin_profiles.user_id...")

    conn = op.get_bind()

    # Check if user_id_temp exists (partial migration)
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'community_admin_profiles'
        AND COLUMN_NAME = 'user_id_temp'
    """))

    has_temp = result.scalar() > 0

    if has_temp:
        print("   ℹ user_id_temp found - completing partial migration...")

        # Drop all FK constraints on user_id
        result = conn.execute(text("""
            SELECT CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'community_admin_profiles'
            AND COLUMN_NAME = 'user_id'
            AND CONSTRAINT_NAME != 'PRIMARY'
        """))

        for row in result:
            constraint_name = row[0]
            try:
                conn.execute(text(f"ALTER TABLE community_admin_profiles DROP FOREIGN KEY {constraint_name}"))
                print(f"      ✓ Dropped FK {constraint_name}")
            except Exception as e:
                print(f"      ⚠ Could not drop FK {constraint_name}: {e}")

        # Drop unique constraint if exists
        try:
            conn.execute(text("ALTER TABLE community_admin_profiles DROP INDEX uq_community_admin_user"))
            print("      ✓ Dropped unique index uq_community_admin_user")
        except Exception:
            print("      ℹ Unique index already dropped or doesn't exist")

        # Now drop the old integer user_id column
        try:
            conn.execute(text("ALTER TABLE community_admin_profiles DROP COLUMN user_id"))
            print("      ✓ Dropped old integer user_id column")
        except Exception as e:
            print(f"      ⚠ Could not drop user_id: {e}")

        # Rename temp to user_id
        conn.execute(text("""
            ALTER TABLE community_admin_profiles
            CHANGE COLUMN user_id_temp user_id VARCHAR(50) NOT NULL UNIQUE
        """))
        print("      ✓ Renamed user_id_temp → user_id")

    else:
        # Check if conversion already complete
        result = conn.execute(text("""
            SELECT DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'community_admin_profiles'
            AND COLUMN_NAME = 'user_id'
        """))

        data_type = result.scalar()

        if data_type and 'varchar' in data_type.lower():
            print("   ✅ user_id already converted to VARCHAR - skipping")
            return
        else:
            print("   ⚠ user_id still INTEGER - conversion not started")
            return

    # Create FK constraint to users.user_id
    try:
        conn.execute(text("""
            ALTER TABLE community_admin_profiles
            ADD CONSTRAINT community_admin_profiles_ibfk_user
            FOREIGN KEY (user_id) REFERENCES users(user_id)
            ON DELETE CASCADE
        """))
        print("      ✓ Created FK to users.user_id")
    except Exception as e:
        print(f"      ⚠ Could not create FK: {e}")

    # Create index
    try:
        conn.execute(text("""
            CREATE INDEX ix_community_admin_profiles_user_id ON community_admin_profiles(user_id)
        """))
        print("      ✓ Created index")
    except Exception:
        print("      ℹ Index already exists")

    print("✅ community_admin_profiles.user_id conversion complete")


def downgrade() -> None:
    """Revert community_admin_profiles.user_id back to INTEGER."""
    print("\n⚠️  Reverting community_admin_profiles.user_id to INTEGER...")

    conn = op.get_bind()

    # Drop FK
    try:
        conn.execute(text("ALTER TABLE community_admin_profiles DROP FOREIGN KEY community_admin_profiles_ibfk_user"))
    except Exception:
        pass

    # Add temp integer column
    conn.execute(text("ALTER TABLE community_admin_profiles ADD COLUMN user_id_temp INT"))

    # Migrate data back
    conn.execute(text("""
        UPDATE community_admin_profiles p
        JOIN users u ON p.user_id = u.user_id
        SET p.user_id_temp = u.id
        WHERE p.user_id IS NOT NULL
    """))

    # Drop string column
    conn.execute(text("ALTER TABLE community_admin_profiles DROP COLUMN user_id"))

    # Rename temp to user_id
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        CHANGE COLUMN user_id_temp user_id INT NOT NULL UNIQUE
    """))

    # Recreate FK to users.id
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        ADD CONSTRAINT community_admin_profiles_ibfk_1
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
    """))

    print("✅ community_admin_profiles.user_id reverted to INT")
