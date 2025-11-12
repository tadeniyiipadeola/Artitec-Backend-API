"""fix_builder_profile_foreign_key

Revision ID: ce3f638a0c53
Revises: e8f29b3c91de
Create Date: 2025-11-06 11:52:35.964142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'ce3f638a0c53'
down_revision: Union[str, Sequence[str], None] = 'e8f29b3c91de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - fix BuilderProfile foreign key to reference users.id instead of users.public_id"""

    # Get connection to execute raw SQL
    conn = op.get_bind()

    # Step 1: Drop existing foreign key constraint if it exists
    result = conn.execute(text("""
        SELECT CONSTRAINT_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME IN ('public_id', 'user_id')
        AND REFERENCED_TABLE_NAME = 'users'
        LIMIT 1
    """))

    row = result.fetchone()
    if row:
        constraint_name = row[0]
        conn.execute(text(f"ALTER TABLE builder_profiles DROP FOREIGN KEY {constraint_name}"))

    # Step 2: Check if column is named public_id and rename it to user_id if needed
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'public_id'
    """))

    count = result.scalar()
    if count > 0:
        # Rename public_id to user_id and change to INT to match users.id
        conn.execute(text("ALTER TABLE builder_profiles CHANGE COLUMN public_id user_id INT(11) NOT NULL"))
    else:
        # Just ensure user_id has correct type (INT to match users.id)
        conn.execute(text("ALTER TABLE builder_profiles MODIFY COLUMN user_id INT(11) NOT NULL"))

    # Step 3: Add correct foreign key constraint
    op.create_foreign_key(
        'builder_profiles_ibfk_user',
        'builder_profiles',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Step 4: Ensure unique index on user_id
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND INDEX_NAME = 'user_id'
        AND NON_UNIQUE = 0
    """))

    count = result.scalar()
    if count == 0:
        conn.execute(text("CREATE UNIQUE INDEX user_id ON builder_profiles(user_id)"))


def downgrade() -> None:
    """Downgrade schema."""
    # This is a fix, so downgrade would revert to the broken state (not recommended)
    # Drop the correct foreign key
    op.drop_constraint('builder_profiles_ibfk_user', 'builder_profiles', type_='foreignkey')

    # Rename column back to public_id (if reverting to old broken state)
    conn = op.get_bind()
    conn.execute(text('ALTER TABLE builder_profiles CHANGE COLUMN user_id public_id INT(11)'))

    # Note: Cannot recreate the incorrect foreign key as it would fail due to type mismatch
