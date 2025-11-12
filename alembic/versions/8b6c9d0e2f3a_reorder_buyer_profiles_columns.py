"""reorder_buyer_profiles_columns

Revision ID: 8b6c9d0e2f3a
Revises: 7a5b8c9d1e2f
Create Date: 2025-11-11 22:35:00.000000

Reorder columns in buyer_profiles table for logical grouping:
1. Keys (id, user_id)
2. Identity (display_name, first_name, last_name)
3. Contact - Canonical (email, phone)
4. Contact - Legacy (contact_email, contact_phone, contact_preferred)
5. Address (address, city, state, zip_code)
6. Profile (profile_image, bio, location, website_url)
7. Demographics (sex)
8. Buying Info (timeline, financing_status, loan_program)
9. Financial (household_income_usd, budget_min_usd, budget_max_usd, down_payment_percent)
10. Agents/Lenders (lender_name, agent_name)
11. Additional (extra)
12. Timestamps (created_at, updated_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '8b6c9d0e2f3a'
down_revision: Union[str, None] = '7a5b8c9d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder columns in buyer_profiles table for better logical organization.
    NOTE: Must drop and recreate foreign keys to reorder FK columns.
    """
    conn = op.get_bind()

    print("🔄 Reordering buyer_profiles columns...")

    # Step 1: Drop foreign key constraint (check if exists first)
    result = conn.execute(text("""
        SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = 'appdb' AND TABLE_NAME = 'buyer_profiles'
        AND REFERENCED_TABLE_NAME IS NOT NULL
    """))
    fk_constraints = [row[0] for row in result]
    for fk_name in fk_constraints:
        conn.execute(text(f"ALTER TABLE buyer_profiles DROP FOREIGN KEY {fk_name}"))

    # id is first (no change needed)

    # user_id after id (fix type to match users.id)
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN user_id INT NOT NULL AFTER id
    """))

    # display_name after user_id
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN display_name VARCHAR(255) AFTER user_id
    """))

    # first_name after display_name
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN first_name VARCHAR(120) AFTER display_name
    """))

    # last_name after first_name
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN last_name VARCHAR(120) AFTER first_name
    """))

    # email after last_name
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN email VARCHAR(255) AFTER last_name
    """))

    # phone after email
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN phone VARCHAR(32) AFTER email
    """))

    # contact_email after phone
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN contact_email VARCHAR(255) AFTER phone
    """))

    # contact_phone after contact_email
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN contact_phone VARCHAR(32) AFTER contact_email
    """))

    # contact_preferred after contact_phone
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN contact_preferred ENUM('email', 'phone', 'sms', 'in_app') NOT NULL DEFAULT 'email' AFTER contact_phone
    """))

    # address after contact_preferred
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN address VARCHAR(255) AFTER contact_preferred
    """))

    # city after address
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN city VARCHAR(120) AFTER address
    """))

    # state after city
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN state VARCHAR(64) AFTER city
    """))

    # zip_code after state
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN zip_code VARCHAR(20) AFTER state
    """))

    # profile_image after zip_code
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN profile_image VARCHAR(500) AFTER zip_code
    """))

    # bio after profile_image
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN bio TEXT AFTER profile_image
    """))

    # location after bio
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN location VARCHAR(255) AFTER bio
    """))

    # website_url after location
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN website_url VARCHAR(512) AFTER location
    """))

    # sex after website_url
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN sex ENUM('female', 'male', 'non_binary', 'other', 'prefer_not') AFTER website_url
    """))

    # timeline after sex
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN timeline ENUM('immediately', 'one_to_three_months', 'three_to_six_months', 'six_plus_months', 'exploring') NOT NULL DEFAULT 'exploring' AFTER sex
    """))

    # financing_status after timeline
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN financing_status ENUM('cash', 'pre_approved', 'pre_qualified', 'needs_pre_approval', 'unknown') NOT NULL DEFAULT 'unknown' AFTER timeline
    """))

    # loan_program after financing_status
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN loan_program ENUM('conventional', 'fha', 'va', 'usda', 'jumbo', 'other') AFTER financing_status
    """))

    # household_income_usd after loan_program
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN household_income_usd INT AFTER loan_program
    """))

    # budget_min_usd after household_income_usd
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN budget_min_usd INT AFTER household_income_usd
    """))

    # budget_max_usd after budget_min_usd
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN budget_max_usd INT AFTER budget_min_usd
    """))

    # down_payment_percent after budget_max_usd
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN down_payment_percent SMALLINT AFTER budget_max_usd
    """))

    # lender_name after down_payment_percent
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN lender_name VARCHAR(255) AFTER down_payment_percent
    """))

    # agent_name after lender_name
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN agent_name VARCHAR(255) AFTER lender_name
    """))

    # extra after agent_name
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN extra JSON AFTER agent_name
    """))

    # created_at after extra
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER extra
    """))

    # updated_at after created_at
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        MODIFY COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at
    """))

    # Step 2: Re-add foreign key constraint
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        ADD CONSTRAINT buyer_profiles_ibfk_1
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """))

    print("✅ buyer_profiles columns reordered successfully!")


def downgrade() -> None:
    """
    No downgrade needed - column order doesn't affect functionality.
    """
    pass
