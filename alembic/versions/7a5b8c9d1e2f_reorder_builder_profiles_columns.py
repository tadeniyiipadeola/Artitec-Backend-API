"""reorder_builder_profiles_columns

Revision ID: 7a5b8c9d1e2f
Revises: 6f9a2e3d8b4c
Create Date: 2025-11-11 22:30:00.000000

Reorder columns in builder_profiles table for logical grouping:
1. Keys (id, user_id, build_id)
2. Core Identity (name, title)
3. Contact (email, phone)
4. Address/Location (address, city, state, postal_code)
5. Profile (about, bio, website, verified)
6. Business (specialties, rating, communities_served, socials)
7. Timestamps (created_at, updated_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '7a5b8c9d1e2f'
down_revision: Union[str, None] = '6f9a2e3d8b4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in builder_profiles table for better logical organization.
    NOTE: Must drop and recreate foreign keys to reorder FK columns.
    """
    conn = op.get_bind()

    print("🔄 Reordering builder_profiles columns...")

    # Step 1: Drop foreign key constraint (check if exists first)
    result = conn.execute(text("""
        SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = 'appdb' AND TABLE_NAME = 'builder_profiles'
        AND CONSTRAINT_NAME = 'builder_profiles_ibfk_user'
    """))
    if result.fetchone():
        conn.execute(text("ALTER TABLE builder_profiles DROP FOREIGN KEY builder_profiles_ibfk_user"))  # user_id FK

    # Reorder columns using ALTER TABLE ... MODIFY COLUMN ... AFTER
    # Order: id, user_id, build_id, name, title, email, phone, address, city, state, postal_code,
    #        about, bio, website, verified, specialties, rating, communities_served, socials,
    #        created_at, updated_at

    # id is first (no change needed)

    # user_id after id
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN user_id INT NOT NULL AFTER id
    """))

    # build_id after user_id
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN build_id VARCHAR(64) NOT NULL AFTER user_id
    """))

    # name after build_id
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN name VARCHAR(255) NOT NULL AFTER build_id
    """))

    # title after name
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN title VARCHAR(128) AFTER name
    """))

    # email after title
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN email VARCHAR(255) AFTER title
    """))

    # phone after email
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN phone VARCHAR(64) AFTER email
    """))

    # address after phone
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN address VARCHAR(255) AFTER phone
    """))

    # city after address
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN city VARCHAR(255) AFTER address
    """))

    # state after city
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN state VARCHAR(64) AFTER city
    """))

    # postal_code after state
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN postal_code VARCHAR(20) AFTER state
    """))

    # about after postal_code
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN about TEXT AFTER postal_code
    """))

    # bio after about
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN bio TEXT AFTER about
    """))

    # website after bio
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN website VARCHAR(1024) AFTER bio
    """))

    # verified after website
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN verified INT DEFAULT 0 AFTER website
    """))

    # specialties after verified
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN specialties JSON AFTER verified
    """))

    # rating after specialties
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN rating FLOAT AFTER specialties
    """))

    # communities_served after rating
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN communities_served JSON AFTER rating
    """))

    # socials after communities_served
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN socials JSON AFTER communities_served
    """))

    # created_at after socials
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER socials
    """))

    # updated_at after created_at
    conn.execute(text("""
        ALTER TABLE builder_profiles
        MODIFY COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at
    """))

    # Step 2: Re-add foreign key constraint
    conn.execute(text("""
        ALTER TABLE builder_profiles
        ADD CONSTRAINT builder_profiles_ibfk_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """))

    print("✅ builder_profiles columns reordered successfully!")


def downgrade() -> None:
    """
    No downgrade needed - column order doesn't affect functionality.
    """
    pass
