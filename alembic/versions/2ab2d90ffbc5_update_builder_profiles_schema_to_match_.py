"""update builder_profiles schema to match model

Revision ID: 2ab2d90ffbc5
Revises: 922b25005b74
Create Date: 2025-11-11 21:02:43.215881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '2ab2d90ffbc5'
down_revision: Union[str, Sequence[str], None] = '922b25005b74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Update builder_profiles table schema to match the model definition.

    Changes:
    - Rename display_name -> name
    - Rename website_url -> website
    - Add build_id (UUID-based identifier)
    - Add new fields: specialties, rating, communities_served, about, phone, email, address, verified, title, socials
    - Drop deprecated fields: logo_url, service_area
    - Keep: bio, city, state, postal_code (already present)
    """
    conn = op.get_bind()

    # Step 1: Rename display_name to name
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'display_name'
    """))
    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE builder_profiles CHANGE COLUMN display_name name VARCHAR(255) NOT NULL"))

    # Step 2: Rename website_url to website
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'website_url'
    """))
    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE builder_profiles CHANGE COLUMN website_url website VARCHAR(1024)"))

    # Step 3: Add build_id column (will be populated with default function)
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'build_id'
    """))
    if result.scalar() == 0:
        # Add without unique constraint first
        op.add_column('builder_profiles', sa.Column('build_id', sa.String(length=64), nullable=True))

        # Generate unique IDs for any existing rows (though there are none currently)
        # This would be done via Python if there was data

        # Make it non-nullable and unique
        conn.execute(text("ALTER TABLE builder_profiles MODIFY COLUMN build_id VARCHAR(64) NOT NULL"))
        conn.execute(text("CREATE UNIQUE INDEX ix_builder_profiles_build_id ON builder_profiles(build_id)"))

    # Step 4: Add new JSON columns
    for col_name in ['specialties', 'communities_served', 'socials']:
        result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = '{col_name}'
        """))
        if result.scalar() == 0:
            op.add_column('builder_profiles', sa.Column(col_name, mysql.JSON(), nullable=True))

    # Step 5: Add numeric columns
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'rating'
    """))
    if result.scalar() == 0:
        op.add_column('builder_profiles', sa.Column('rating', sa.Float(), nullable=True))

    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'verified'
    """))
    if result.scalar() == 0:
        op.add_column('builder_profiles', sa.Column('verified', sa.Integer(), server_default='0', nullable=True))

    # Step 6: Add text/string columns
    new_columns = {
        'about': ('TEXT', True),
        'phone': ('VARCHAR(64)', True),
        'email': ('VARCHAR(255)', True),
        'address': ('VARCHAR(255)', True),
        'title': ('VARCHAR(128)', True),
    }

    for col_name, (col_type, nullable) in new_columns.items():
        result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = '{col_name}'
        """))
        if result.scalar() == 0:
            null_str = "NULL" if nullable else "NOT NULL"
            conn.execute(text(f"ALTER TABLE builder_profiles ADD COLUMN {col_name} {col_type} {null_str}"))

    # Step 7: Drop deprecated columns
    for col_name in ['logo_url', 'service_area']:
        result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = '{col_name}'
        """))
        if result.scalar() > 0:
            conn.execute(text(f"ALTER TABLE builder_profiles DROP COLUMN {col_name}"))


def downgrade() -> None:
    """
    Downgrade schema back to original structure.
    Note: This is a destructive operation and will lose data in new columns.
    """
    conn = op.get_bind()

    # Reverse: Add back old columns
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'logo_url'
    """))
    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE builder_profiles ADD COLUMN logo_url VARCHAR(255)"))

    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'service_area'
    """))
    if result.scalar() == 0:
        conn.execute(text("ALTER TABLE builder_profiles ADD COLUMN service_area VARCHAR(255)"))

    # Reverse: Drop new columns
    for col_name in ['about', 'phone', 'email', 'address', 'title', 'verified', 'rating',
                     'specialties', 'communities_served', 'socials', 'build_id']:
        result = conn.execute(text(f"""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = '{col_name}'
        """))
        if result.scalar() > 0:
            # Drop index if exists
            if col_name == 'build_id':
                conn.execute(text("DROP INDEX IF EXISTS ix_builder_profiles_build_id ON builder_profiles"))
            conn.execute(text(f"ALTER TABLE builder_profiles DROP COLUMN {col_name}"))

    # Reverse: Rename columns back
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'name'
    """))
    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE builder_profiles CHANGE COLUMN name display_name VARCHAR(150) NOT NULL"))

    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'builder_profiles'
        AND COLUMN_NAME = 'website'
    """))
    if result.scalar() > 0:
        conn.execute(text("ALTER TABLE builder_profiles CHANGE COLUMN website website_url VARCHAR(255)"))
