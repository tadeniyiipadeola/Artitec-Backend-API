"""migrate_community_builders_to_public_id

Revision ID: 0b3bc8ec2b37
Revises: ffa0a165788d
Create Date: 2025-12-09 18:52:04.247510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0b3bc8ec2b37'
down_revision: Union[str, Sequence[str], None] = 'ffa0a165788d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - migrate community_builders to public community_id."""

    table = 'community_builders'

    # Check if table exists
    result = op.get_bind().execute(text(f"""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = '{table}'
    """))
    if result.scalar() == 0:
        print(f'Skipping {table} - table does not exist')
        return

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

        if data_type in ('int', 'bigint'):
            op.execute(text(f"""
                ALTER TABLE {table}
                CHANGE COLUMN community_id community_numeric_id BIGINT UNSIGNED
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


def downgrade() -> None:
    """Downgrade schema - revert to numeric community_id."""

    table = 'community_builders'

    # Step 1: Drop new foreign key constraint
    op.execute(text(f"""
        ALTER TABLE {table}
        DROP FOREIGN KEY IF EXISTS fk_{table}_community_id_public
    """))

    # Step 2: Drop index
    op.execute(text(f"""
        DROP INDEX IF EXISTS idx_{table}_community_id ON {table}
    """))

    # Step 3: Drop the community_id VARCHAR column
    op.execute(text(f"""
        ALTER TABLE {table}
        DROP COLUMN community_id
    """))

    # Step 4: Rename community_numeric_id back to community_id
    op.execute(text(f"""
        ALTER TABLE {table}
        CHANGE COLUMN community_numeric_id community_id BIGINT UNSIGNED
    """))

    # Step 5: Recreate original foreign key constraint
    op.execute(text(f"""
        ALTER TABLE {table}
        ADD CONSTRAINT fk_{table}_community_id
        FOREIGN KEY (community_id) REFERENCES communities(id)
        ON DELETE CASCADE
    """))

    # Step 6: Recreate index
    op.execute(text(f"""
        CREATE INDEX idx_{table}_community_id ON {table}(community_id)
    """))
