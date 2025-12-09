"""migrate_community_relations_to_public_id

Revision ID: ffa0a165788d
Revises: 0321a7bd0e29
Create Date: 2025-12-08 20:44:32.066997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'ffa0a165788d'
down_revision: Union[str, Sequence[str], None] = '0321a7bd0e29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - migrate to public community_id."""

    # Tables that have community_id foreign key to communities table
    tables = [
        'community_awards',
        'community_amenities',
        'community_admins',
        'community_events',
        'community_phases',
        'community_builder_cards',
        'community_threads'
    ]

    for table in tables:
        # Check if table exists
        result = op.get_bind().execute(text(f"""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = '{table}'
        """))
        if result.scalar() == 0:
            print(f'Skipping {table} - table does not exist')
            continue

        # Get current column names
        result = op.get_bind().execute(text(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = '{table}'
        """))
        columns = {row[0] for row in result.fetchall()}

        # Step 1: Drop existing foreign key constraints if they exist
        result = op.get_bind().execute(text(f"""
            SELECT constraint_name FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND table_name = '{table}'
            AND referenced_table_name IS NOT NULL
        """))
        for fk in result.fetchall():
            op.execute(text(f"ALTER TABLE {table} DROP FOREIGN KEY {fk[0]}"))

        # Step 2: Rename community_id to community_numeric_id (if not already done)
        if 'community_id' in columns and 'community_numeric_id' not in columns:
            # Check if community_id is int type
            result = op.get_bind().execute(text(f"""
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = '{table}'
                AND column_name = 'community_id'
            """))
            data_type = result.scalar()

            if data_type == 'int':
                op.execute(text(f"""
                    ALTER TABLE {table}
                    CHANGE COLUMN community_id community_numeric_id INT
                """))
                columns.remove('community_id')
                columns.add('community_numeric_id')

        # Step 3: Add new community_id VARCHAR column (if it doesn't exist)
        if 'community_id' not in columns:
            op.execute(text(f"""
                ALTER TABLE {table}
                ADD COLUMN community_id VARCHAR(50) NULL AFTER community_numeric_id
            """))
            columns.add('community_id')

        # Step 4: Populate community_id with public IDs from communities table
        op.execute(text(f"""
            UPDATE {table} t
            JOIN communities c ON t.community_numeric_id = c.id
            SET t.community_id = c.community_id
            WHERE t.community_id IS NULL OR t.community_id = ''
        """))

        # Step 5: Make community_id NOT NULL
        op.execute(text(f"""
            ALTER TABLE {table}
            MODIFY COLUMN community_id VARCHAR(50) NOT NULL
        """))

        # Step 6: Drop old index if it exists, then create new one
        result = op.get_bind().execute(text(f"""
            SELECT DISTINCT index_name FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND table_name = '{table}'
            AND index_name = 'idx_{table}_community_id'
        """))
        if result.fetchone():
            op.execute(text(f"DROP INDEX idx_{table}_community_id ON {table}"))

        op.execute(text(f"""
            CREATE INDEX idx_{table}_community_id ON {table}(community_id)
        """))

        # Step 7: Add foreign key constraint to communities.community_id
        op.execute(text(f"""
            ALTER TABLE {table}
            ADD CONSTRAINT fk_{table}_community_id_public
            FOREIGN KEY (community_id) REFERENCES communities(community_id)
            ON DELETE CASCADE
        """))

        # Step 8: Add created_at and updated_at timestamp columns (if they don't exist)
        if 'created_at' not in columns:
            op.execute(text(f"""
                ALTER TABLE {table}
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))

        if 'updated_at' not in columns:
            op.execute(text(f"""
                ALTER TABLE {table}
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """))


def downgrade() -> None:
    """Downgrade schema - revert to numeric community_id."""

    tables = [
        'community_awards',
        'community_amenities',
        'community_admins',
        'community_events',
        'community_phases',
        'community_builder_cards',
        'community_threads'
    ]

    for table in tables:
        # Step 1: Drop created_at and updated_at columns
        op.execute(f"""
            ALTER TABLE {table}
            DROP COLUMN IF EXISTS created_at,
            DROP COLUMN IF EXISTS updated_at
        """)

        # Step 2: Drop new foreign key constraint
        op.execute(f"""
            ALTER TABLE {table}
            DROP FOREIGN KEY IF EXISTS fk_{table}_community_id_public
        """)

        # Step 3: Drop index
        op.execute(f"""
            DROP INDEX IF EXISTS idx_{table}_community_id ON {table}
        """)

        # Step 4: Drop the community_id VARCHAR column
        op.execute(f"""
            ALTER TABLE {table}
            DROP COLUMN community_id
        """)

        # Step 5: Rename community_numeric_id back to community_id
        op.execute(f"""
            ALTER TABLE {table}
            CHANGE COLUMN community_numeric_id community_id INT
        """)

        # Step 6: Recreate original foreign key constraint
        op.execute(f"""
            ALTER TABLE {table}
            ADD CONSTRAINT fk_{table}_community_id
            FOREIGN KEY (community_id) REFERENCES communities(id)
            ON DELETE CASCADE
        """)

        # Step 7: Recreate index
        op.execute(f"""
            CREATE INDEX idx_{table}_community_id ON {table}(community_id)
        """)
