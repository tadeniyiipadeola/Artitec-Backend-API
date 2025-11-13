"""rename_public_id_to_typed_ids

Revision ID: 43f361179508
Revises: fc09f3d9770a
Create Date: 2025-11-12 22:31:20.385348

Rename public_id columns to typed IDs:
- users.public_id → user_id
- communities.public_id → community_id
- buyer_profiles.public_id → buyer_id
- builder_profiles.public_id → builder_id
- sales_reps.public_id → sales_rep_id
- community_admin_profiles.public_id → community_admin_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '43f361179508'
down_revision: Union[str, Sequence[str], None] = 'fc09f3d9770a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename public_id columns to typed IDs."""
    print("\n🔧 Renaming public_id columns to typed IDs...")

    conn = op.get_bind()

    # 1. users.public_id → user_id
    print("   1/6 Renaming users.public_id → user_id...")
    conn.execute(text("""
        ALTER TABLE users
        CHANGE COLUMN public_id user_id VARCHAR(50) NOT NULL
    """))
    print("      ✓ users.user_id")

    # 2. communities.public_id → community_id
    print("   2/6 Renaming communities.public_id → community_id...")
    conn.execute(text("""
        ALTER TABLE communities
        CHANGE COLUMN public_id community_id VARCHAR(64) NOT NULL
    """))
    print("      ✓ communities.community_id")

    # 3. buyer_profiles.public_id → buyer_id
    print("   3/6 Renaming buyer_profiles.public_id → buyer_id...")
    conn.execute(text("""
        ALTER TABLE buyer_profiles
        CHANGE COLUMN public_id buyer_id VARCHAR(64) NOT NULL
    """))
    print("      ✓ buyer_profiles.buyer_id")

    # 4. builder_profiles.public_id → builder_id
    print("   4/6 Renaming builder_profiles.public_id → builder_id...")
    conn.execute(text("""
        ALTER TABLE builder_profiles
        CHANGE COLUMN public_id builder_id VARCHAR(64) NOT NULL
    """))
    print("      ✓ builder_profiles.builder_id")

    # 5. sales_reps.public_id → sales_rep_id
    print("   5/6 Renaming sales_reps.public_id → sales_rep_id...")
    conn.execute(text("""
        ALTER TABLE sales_reps
        CHANGE COLUMN public_id sales_rep_id VARCHAR(64) NOT NULL
    """))
    print("      ✓ sales_reps.sales_rep_id")

    # 6. community_admin_profiles.public_id → community_admin_id
    print("   6/6 Renaming community_admin_profiles.public_id → community_admin_id...")
    conn.execute(text("""
        ALTER TABLE community_admin_profiles
        CHANGE COLUMN public_id community_admin_id VARCHAR(64) NOT NULL
    """))
    print("      ✓ community_admin_profiles.community_admin_id")

    print("\n✅ All public_id columns renamed to typed IDs")


def downgrade() -> None:
    """Revert typed IDs back to public_id."""
    print("\n⚠️  Reverting typed IDs back to public_id...")

    conn = op.get_bind()

    # Reverse all changes
    conn.execute(text("ALTER TABLE users CHANGE COLUMN user_id public_id VARCHAR(50) NOT NULL"))
    conn.execute(text("ALTER TABLE communities CHANGE COLUMN community_id public_id VARCHAR(64) NOT NULL"))
    conn.execute(text("ALTER TABLE buyer_profiles CHANGE COLUMN buyer_id public_id VARCHAR(64) NOT NULL"))
    conn.execute(text("ALTER TABLE builder_profiles CHANGE COLUMN builder_id public_id VARCHAR(64) NOT NULL"))
    conn.execute(text("ALTER TABLE sales_reps CHANGE COLUMN sales_rep_id public_id VARCHAR(64) NOT NULL"))
    conn.execute(text("ALTER TABLE community_admin_profiles CHANGE COLUMN community_admin_id public_id VARCHAR(64) NOT NULL"))

    print("✅ All columns reverted to public_id")
