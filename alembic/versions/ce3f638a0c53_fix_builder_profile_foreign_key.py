"""fix_builder_profile_foreign_key

Revision ID: ce3f638a0c53
Revises: e8f29b3c91de
Create Date: 2025-11-06 11:52:35.964142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce3f638a0c53'
down_revision: Union[str, Sequence[str], None] = 'e8f29b3c91de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fix BuilderProfile foreign key to reference users.id instead of users.public_id

    # Step 1: Drop existing foreign key constraint if it exists
    # The constraint name may vary, so we use a try-except approach via raw SQL
    op.execute("""
        SET @constraint_name = (
            SELECT CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME IN ('public_id', 'user_id')
            AND REFERENCED_TABLE_NAME = 'users'
            LIMIT 1
        );

        SET @drop_fk_sql = IF(
            @constraint_name IS NOT NULL,
            CONCAT('ALTER TABLE builder_profiles DROP FOREIGN KEY ', @constraint_name),
            'SELECT 1'
        );

        PREPARE stmt FROM @drop_fk_sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """)

    # Step 2: Check if column is named public_id and rename it to user_id if needed
    op.execute("""
        SET @column_exists = (
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = 'public_id'
        );

        SET @rename_sql = IF(
            @column_exists > 0,
            'ALTER TABLE builder_profiles CHANGE COLUMN public_id user_id BIGINT UNSIGNED NOT NULL',
            'ALTER TABLE builder_profiles MODIFY COLUMN user_id BIGINT UNSIGNED NOT NULL'
        );

        PREPARE stmt FROM @rename_sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """)

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
    op.execute("""
        SET @index_exists = (
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'builder_profiles'
            AND INDEX_NAME = 'user_id'
            AND NON_UNIQUE = 0
        );

        SET @create_index_sql = IF(
            @index_exists = 0,
            'CREATE UNIQUE INDEX user_id ON builder_profiles(user_id)',
            'SELECT 1'
        );

        PREPARE stmt FROM @create_index_sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # This is a fix, so downgrade would revert to the broken state (not recommended)
    # Drop the correct foreign key
    op.drop_constraint('builder_profiles_ibfk_user', 'builder_profiles', type_='foreignkey')

    # Rename column back to public_id (if reverting to old broken state)
    op.execute('ALTER TABLE builder_profiles CHANGE COLUMN user_id public_id BIGINT UNSIGNED')

    # Recreate the incorrect foreign key (for reference only - this will fail due to type mismatch)
    # op.create_foreign_key(
    #     'builder_profiles_ibfk_1',
    #     'builder_profiles',
    #     'users',
    #     ['public_id'],
    #     ['public_id'],  # This would fail: BIGINT -> VARCHAR
    #     ondelete='SET NULL'
    # )
