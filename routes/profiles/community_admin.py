# routes/profiles/community_admin.py
"""
API routes for Community Admin Profiles
Manages the profiles of users who are community administrators
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.db import get_db
from config.security import get_current_user_optional, get_current_user
from model.profiles.community_admin_profile import CommunityAdminProfile
from model.user import Users
from schema.community_admin_profile import (
    CommunityAdminProfileOut,
    CommunityAdminProfileCreate,
    CommunityAdminProfileUpdate
)


router = APIRouter()


# -------------------- Helper Functions --------------------

def _get_profile_or_404(db: Session, profile_id: int) -> CommunityAdminProfile:
    """Get community admin profile by ID or raise 404"""
    profile = db.query(CommunityAdminProfile).filter(
        CommunityAdminProfile.id == profile_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Community admin profile not found")
    return profile


def _get_profile_by_user_id(db: Session, user_id: str) -> Optional[CommunityAdminProfile]:
    """Get community admin profile by user_id (returns None if not found)"""
    return db.query(CommunityAdminProfile).filter(
        CommunityAdminProfile.user_id == user_id
    ).first()


def _build_profile_out(profile: CommunityAdminProfile) -> dict:
    """Build response dict with profile data"""
    data = {
        "id": profile.id,
        "user_id": profile.user_id,
        "community_id": profile.community_id,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "profile_image": profile.profile_image,
        "bio": profile.bio,
        "title": profile.title,
        "contact_email": profile.contact_email,
        "contact_phone": profile.contact_phone,
        "contact_preferred": profile.contact_preferred,
        "can_post_announcements": profile.can_post_announcements,
        "can_manage_events": profile.can_manage_events,
        "can_moderate_threads": profile.can_moderate_threads,
        "extra": profile.extra,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }

    return data


# -------------------- CRUD Endpoints --------------------

@router.get("/me", response_model=CommunityAdminProfileOut)
def get_my_community_admin_profile(
    *,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get the current user's community admin profile"""
    print(f"🔍 GET /community-admins/me: user_id={current_user.user_id}")

    profile = _get_profile_by_user_id(db, current_user.user_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Community admin profile not found for current user"
        )

    return CommunityAdminProfileOut(**_build_profile_out(profile))


@router.get("/{profile_id}", response_model=CommunityAdminProfileOut)
def get_community_admin_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: int,
    current_user=Depends(get_current_user_optional)
):
    """Get a community admin profile by ID"""
    print(f"🔍 GET /community-admins/{profile_id}")

    profile = _get_profile_or_404(db, profile_id)
    return CommunityAdminProfileOut(**_build_profile_out(profile))


@router.get("/user/{user_id}", response_model=CommunityAdminProfileOut)
def get_community_admin_profile_by_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    current_user=Depends(get_current_user_optional)
):
    """Get a community admin profile by user_id"""
    print(f"🔍 GET /community-admins/user/{user_id}")

    profile = _get_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Community admin profile not found for user")

    return CommunityAdminProfileOut(**_build_profile_out(profile))


@router.post("/", response_model=CommunityAdminProfileOut, status_code=status.HTTP_201_CREATED)
def create_community_admin_profile(
    *,
    db: Session = Depends(get_db),
    payload: CommunityAdminProfileCreate,
    current_user: Users = Depends(get_current_user)
):
    """Create a new community admin profile for the current user"""
    print(f"📝 POST /community-admins: user_id={current_user.user_id}, community_id={payload.community_id}")

    # Check if profile already exists for this user
    existing = _get_profile_by_user_id(db, current_user.user_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Community admin profile already exists for current user"
        )

    # Create new profile with current user's ID
    profile_data = payload.model_dump()
    profile_data["user_id"] = current_user.user_id  # Override user_id with current user
    profile = CommunityAdminProfile(**profile_data)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    print(f"✅ Created community admin profile: id={profile.id}")
    return CommunityAdminProfileOut(**_build_profile_out(profile))


@router.patch("/{profile_id}", response_model=CommunityAdminProfileOut)
def update_community_admin_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: int,
    payload: CommunityAdminProfileUpdate,
    current_user: Users = Depends(get_current_user)
):
    """Update a community admin profile"""
    print(f"🔧 PATCH /community-admins/{profile_id}")

    profile = _get_profile_or_404(db, profile_id)

    # Update fields
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)

    print(f"✅ Updated community admin profile: id={profile.id}")
    return CommunityAdminProfileOut(**_build_profile_out(profile))


@router.patch("/me", response_model=CommunityAdminProfileOut)
def update_my_community_admin_profile(
    *,
    db: Session = Depends(get_db),
    payload: CommunityAdminProfileUpdate,
    current_user: Users = Depends(get_current_user)
):
    """Update the current user's community admin profile"""
    print(f"🔧 PATCH /community-admins/me: user_id={current_user.user_id}")

    profile = _get_profile_by_user_id(db, current_user.user_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Community admin profile not found for current user"
        )

    # Update fields
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)

    print(f"✅ Updated community admin profile: id={profile.id}")
    return CommunityAdminProfileOut(**_build_profile_out(profile))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_community_admin_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: int,
    current_user: Users = Depends(get_current_user)
):
    """Delete a community admin profile"""
    print(f"🗑️  DELETE /community-admins/{profile_id}")

    profile = _get_profile_or_404(db, profile_id)
    db.delete(profile)
    db.commit()

    print(f"✅ Deleted community admin profile: id={profile_id}")
    return None
