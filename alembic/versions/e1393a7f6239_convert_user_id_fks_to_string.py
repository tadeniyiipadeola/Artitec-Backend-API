"""convert_user_id_fks_to_string

Revision ID: e1393a7f6239
Revises: 396dd510e408
Create Date: 2025-11-12 22:41:24.097318

Convert all user_id FK columns from INTEGER (referencing users.id)
to VARCHAR(50) (referencing users.user_id string).

Affects tables:
- buyer_profiles.user_id
- builder_profiles.user_id
- communities.user_id (owner)
- sales_reps.user_id
- community_admin_profiles.user_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'e1393a7f6239'
down_revision: Union[str, Sequence[str], None] = '396dd510e408'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert user_id FKs from INTEGER to VARCHAR(50) referencing users.user_id."""
    print("\n🔧 Converting user_id FK columns to string type...")

    conn = op.get_bind()

    # List of tables and their constraints to convert
    tables = [
        ('buyer_profiles', 'buyer_profiles_ibfk_1', True),  # (table, fk_constraint, unique)
        ('builder_profiles', 'builder_profiles_ibfk_user', True),
        ('communities', 'fk_communities_user_id', False),
        ('sales_reps', 'fk_sales_reps_user_id', False),
        ('community_admin_profiles', 'community_admin_profiles_ibfk_1', True),
    ]

    for table_name, fk_name, is_unique in tables:
        print(f"\n   Converting {table_name}.user_id...")

        # 1. Drop existing FK constraint
        try:
            conn.execute(text(f"ALTER TABLE {table_name} DROP FOREIGN KEY {fk_name}"))
            print(f"      ✓ Dropped FK constraint {fk_name}")
        except Exception as e:
            print(f"      ⚠ FK {fk_name} not found: {e}")

        # 2. Add temporary column for string user_id
        conn.execute(text(f"""
            ALTER TABLE {table_name}
            ADD COLUMN user_id_temp VARCHAR(50)
        """))
        print(f"      ✓ Added user_id_temp column")

        # 3. Migrate data: copy string user_id from users table
        conn.execute(text(f"""
            UPDATE {table_name} p
            JOIN users u ON p.user_id = u.id
            SET p.user_id_temp = u.user_id
            WHERE p.user_id IS NOT NULL
        """))
        print(f"      ✓ Migrated data to user_id_temp")

        # 4. Drop old integer user_id column
        conn.execute(text(f"""
            ALTER TABLE {table_name}
            DROP COLUMN user_id
        """))
        print(f"      ✓ Dropped old integer user_id")

        # 5. Rename temp column to user_id
        nullable = "NULL" if not is_unique else "NOT NULL"
        unique_str = "UNIQUE" if is_unique else ""
        conn.execute(text(f"""
            ALTER TABLE {table_name}
            CHANGE COLUMN user_id_temp user_id VARCHAR(50) {nullable} {unique_str}
        """))
        print(f"      ✓ Renamed user_id_temp → user_id")

        # 6. Create new FK constraint to users.user_id
        conn.execute(text(f"""
            ALTER TABLE {table_name}
            ADD CONSTRAINT {fk_name}
            FOREIGN KEY (user_id) REFERENCES users(user_id)
            ON DELETE CASCADE
        """))
        print(f"      ✓ Created FK to users.user_id")

        # 7. Create index
        try:
            conn.execute(text(f"""
                CREATE INDEX ix_{table_name}_user_id ON {table_name}(user_id)
            """))
            print(f"      ✓ Created index")
        except Exception:
            print(f"      ℹ Index already exists")

    print("\n✅ All user_id columns converted to VARCHAR(50) FK to users.user_id")


def downgrade() -> None:
    """Revert user_id FKs back to INTEGER referencing users.id."""
    print("\n⚠️  Reverting user_id columns back to INTEGER...")

    conn = op.get_bind()

    tables = [
        ('buyer_profiles', 'buyer_profiles_ibfk_1', True),
        ('builder_profiles', 'builder_profiles_ibfk_user', True),
        ('communities', 'fk_communities_user_id', False),
        ('sales_reps', 'fk_sales_reps_user_id', False),
        ('community_admin_profiles', 'community_admin_profiles_ibfk_1', True),
    ]

    for table_name, fk_name, is_unique in tables:
        print(f"\n   Reverting {table_name}.user_id...")

        # Drop FK
        conn.execute(text(f"ALTER TABLE {table_name} DROP FOREIGN KEY {fk_name}"))

        # Add temp integer column
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id_temp INT"))

        # Migrate data back
        conn.execute(text(f"""
            UPDATE {table_name} p
            JOIN users u ON p.user_id = u.user_id
            SET p.user_id_temp = u.id
            WHERE p.user_id IS NOT NULL
        """))

        # Drop string column
        conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN user_id"))

        # Rename temp to user_id
        nullable = "NULL" if not is_unique else "NOT NULL"
        unique_str = "UNIQUE" if is_unique else ""
        conn.execute(text(f"""
            ALTER TABLE {table_name}
            CHANGE COLUMN user_id_temp user_id INT {nullable} {unique_str}
        """))

        # Recreate FK to users.id
        conn.execute(text(f"""
            ALTER TABLE {table_name}
            ADD CONSTRAINT {fk_name}
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE
        """))

    print("\n✅ All user_id columns reverted to INT FK to users.id")
