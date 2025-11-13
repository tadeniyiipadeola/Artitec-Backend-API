# routes/admin_helpers.py
"""
Admin helper endpoints for database management tasks
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from config.db import get_db
from src.id_generator import generate_community_admin_id

router = APIRouter()


@router.post("/connect-user-to-community")
def connect_user_to_community(
    user_email: str = None,
    user_public_id: str = None,
    community_name: str = None,
    community_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Connect a user to a community by creating/updating CommunityAdminProfile.

    Example:
        POST /admin/connect-user-to-community?user_email=fred.caldwell@oakmeadows.org&community_name=The Highlands
        POST /admin/connect-user-to-community?user_public_id=USR-1763002155-GRZVLL&community_name=The Highlands
    """

    if not (user_email or user_public_id):
        raise HTTPException(status_code=400, detail="Must provide user_email or user_public_id")

    if not (community_name or community_id):
        raise HTTPException(status_code=400, detail="Must provide community_name or community_id")

    # Find user
    if user_public_id:
        result = db.execute(text("""
            SELECT id, user_id, email, first_name, last_name, phone_e164, role
            FROM users
            WHERE user_id = :user_id
            LIMIT 1
        """), {"user_id": user_public_id})
    else:
        result = db.execute(text("""
            SELECT id, user_id, email, first_name, last_name, phone_e164, role
            FROM users
            WHERE email = :email
            LIMIT 1
        """), {"email": user_email})

    user = result.fetchone()

    if not user:
        identifier = user_public_id or user_email
        raise HTTPException(status_code=404, detail=f"User not found: {identifier}")

    # Find community
    if community_id:
        result = db.execute(text("""
            SELECT id, community_id, name
            FROM communities
            WHERE id = :id
            LIMIT 1
        """), {"id": community_id})
    else:
        result = db.execute(text("""
            SELECT id, community_id, name
            FROM communities
            WHERE name LIKE :name
            LIMIT 1
        """), {"name": f"%{community_name}%"})

    community = result.fetchone()

    if not community:
        raise HTTPException(status_code=404, detail=f"Community not found: {community_name}")

    # Check if admin profile exists
    result = db.execute(text("""
        SELECT id, community_admin_id, community_id
        FROM community_admin_profiles
        WHERE user_id = :user_id
    """), {"user_id": user.user_id})

    existing = result.fetchone()

    if existing:
        # Update existing
        db.execute(text("""
            UPDATE community_admin_profiles
            SET community_id = :community_id,
                first_name = :first_name,
                last_name = :last_name,
                contact_email = :email,
                contact_phone = :phone,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """), {
            "user_id": user.user_id,
            "community_id": community.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone_e164
        })
        action = "updated"
        admin_typed_id = existing.community_admin_id
    else:
        # Create new
        admin_typed_id = generate_community_admin_id()
        db.execute(text("""
            INSERT INTO community_admin_profiles (
                community_admin_id, user_id, community_id,
                first_name, last_name, contact_email, contact_phone,
                title, can_post_announcements, can_manage_events, can_moderate_threads
            ) VALUES (
                :community_admin_id, :user_id, :community_id,
                :first_name, :last_name, :email, :phone,
                'Community Administrator', 1, 1, 1
            )
        """), {
            "community_admin_id": admin_typed_id,
            "user_id": user.user_id,
            "community_id": community.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone_e164
        })
        action = "created"

    db.commit()

    return {
        "success": True,
        "action": action,
        "user": {
            "id": user.id,
            "user_id": user.user_id,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}",
            "role": user.role
        },
        "community": {
            "id": community.id,
            "community_id": community.community_id,
            "name": community.name
        },
        "admin_profile_community_admin_id": admin_typed_id,
        "endpoint": f"/api/v1/communities/for-user/{user.user_id}"
    }
