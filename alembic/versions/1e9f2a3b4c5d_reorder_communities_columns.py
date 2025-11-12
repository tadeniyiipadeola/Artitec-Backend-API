"""reorder_communities_columns

Revision ID: 1e9f2a3b4c5d
Revises: 0d8e1f2a3b4c
Create Date: 2025-11-11 22:50:00.000000

Reorder columns in communities table for logical grouping:
1. Keys (id, public_id)
2. Core Identity (name)
3. Location (city, state, postal_code)
4. Financial (community_dues, tax_rate, monthly_fee)
5. Profile (about, is_verified)
6. Stats (followers, homes, residents, founded_year, member_count)
7. Development (development_stage, enterprise_number_hoa)
8. Media (intro_video_url, community_website_url)
9. Timestamps (created_at, updated_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '1e9f2a3b4c5d'
down_revision: Union[str, None] = '0d8e1f2a3b4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in communities table for better logical organization.
    """
    conn = op.get_bind()

    print("🔄 Reordering communities columns...")

    # id is first (no change needed)

    # public_id after id
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN public_id VARCHAR(64) NOT NULL AFTER id
    """))

    # name after public_id
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN name VARCHAR(255) NOT NULL AFTER public_id
    """))

    # city after name
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN city VARCHAR(255) AFTER name
    """))

    # state after city
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN state VARCHAR(64) AFTER city
    """))

    # postal_code after state
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN postal_code VARCHAR(20) AFTER state
    """))

    # community_dues after postal_code
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN community_dues VARCHAR(64) AFTER postal_code
    """))

    # tax_rate after community_dues
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN tax_rate VARCHAR(32) AFTER community_dues
    """))

    # monthly_fee after tax_rate
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN monthly_fee VARCHAR(64) AFTER tax_rate
    """))

    # about after monthly_fee
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN about TEXT AFTER monthly_fee
    """))

    # followers after about (is_verified doesn't exist in table)
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN followers INT DEFAULT 0 AFTER about
    """))

    # homes after followers
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN homes INT DEFAULT 0 AFTER followers
    """))

    # residents after homes
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN residents INT DEFAULT 0 AFTER homes
    """))

    # founded_year after residents
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN founded_year INT AFTER residents
    """))

    # member_count after founded_year
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN member_count INT DEFAULT 0 AFTER founded_year
    """))

    # development_stage after member_count
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN development_stage VARCHAR(64) AFTER member_count
    """))

    # enterprise_number_hoa after development_stage
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN enterprise_number_hoa VARCHAR(255) AFTER development_stage
    """))

    # intro_video_url after enterprise_number_hoa
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN intro_video_url VARCHAR(1024) AFTER enterprise_number_hoa
    """))

    # community_website_url after intro_video_url
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN community_website_url VARCHAR(1024) AFTER intro_video_url
    """))

    # created_at after community_website_url
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER community_website_url
    """))

    # updated_at after created_at
    conn.execute(text("""
        ALTER TABLE communities
        MODIFY COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at
    """))

    print("✅ communities columns reordered successfully!")


def downgrade() -> None:
    """
    No downgrade needed - column order doesn't affect functionality.
    """
    pass
