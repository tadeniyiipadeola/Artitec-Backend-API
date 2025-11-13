"""set_highlands_owner_user_id

Revision ID: fc09f3d9770a
Revises: g3h4i5j6k7l8
Create Date: 2025-11-12 22:17:40.976995

Data migration to set The Highlands community owner to Fred Caldwell.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'fc09f3d9770a'
down_revision: Union[str, Sequence[str], None] = 'g3h4i5j6k7l8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set The Highlands community owner to Fred Caldwell user."""
    print("\n🔧 Updating The Highlands community owner...")

    conn = op.get_bind()

    # Find the user with public_id USR-1763002155-GRZVLL
    result = conn.execute(text("""
        SELECT id, public_id, email, first_name, last_name
        FROM users
        WHERE public_id = :public_id
        LIMIT 1
    """), {"public_id": "USR-1763002155-GRZVLL"})

    user = result.fetchone()

    if not user:
        print("   ⚠️  User USR-1763002155-GRZVLL not found - skipping update")
        print("   ℹ️  This is OK if the user hasn't been created yet")
        return

    user_id, user_public_id, user_email, first_name, last_name = user

    print(f"   ✓ Found user: {first_name} {last_name} ({user_email})")
    print(f"     User ID: {user_id}")

    # Find The Highlands community
    result = conn.execute(text("""
        SELECT id, public_id, name, user_id
        FROM communities
        WHERE name LIKE :name
        LIMIT 1
    """), {"name": "%Highlands%"})

    community = result.fetchone()

    if not community:
        print("   ⚠️  The Highlands community not found - skipping update")
        print("   ℹ️  This is OK if the community hasn't been created yet")
        return

    community_id, community_public_id, community_name, current_user_id = community

    print(f"   ✓ Found community: {community_name}")
    print(f"     Community ID: {community_id}")
    print(f"     Current user_id: {current_user_id or 'None'}")

    # Check if already set
    if current_user_id == user_id:
        print(f"   ℹ️  Community already owned by {first_name} {last_name}")
        return

    # Update the community
    conn.execute(text("""
        UPDATE communities
        SET user_id = :user_id
        WHERE id = :community_id
    """), {"user_id": user_id, "community_id": community_id})

    print(f"   ✅ Updated '{community_name}' owner")
    print(f"      Owner: {first_name} {last_name}")
    print(f"      User ID: {user_id} (public_id: {user_public_id})")


def downgrade() -> None:
    """Remove The Highlands community owner."""
    print("\n⚠️  Removing The Highlands community owner...")

    conn = op.get_bind()

    # Find The Highlands community
    result = conn.execute(text("""
        SELECT id, name, user_id
        FROM communities
        WHERE name LIKE :name
        LIMIT 1
    """), {"name": "%Highlands%"})

    community = result.fetchone()

    if not community:
        print("   ℹ️  The Highlands community not found - nothing to downgrade")
        return

    community_id, community_name, current_user_id = community

    if current_user_id is None:
        print(f"   ℹ️  '{community_name}' has no owner - nothing to downgrade")
        return

    # Set user_id back to NULL
    conn.execute(text("""
        UPDATE communities
        SET user_id = NULL
        WHERE id = :community_id
    """), {"community_id": community_id})

    print(f"   ✅ Removed owner from '{community_name}'")
    print(f"      Previous user_id: {current_user_id} → NULL")
