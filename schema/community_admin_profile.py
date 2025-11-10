# schema/community_admin_profile.py
"""
Pydantic schemas for Community Admin Profiles
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, constr, EmailStr, Field

# Pydantic v2/v1 compatibility
try:
    from pydantic import ConfigDict
    _HAS_V2 = True
except Exception:
    _HAS_V2 = False


# -------------------- Base Schema --------------------
class CommunityAdminProfileBase(BaseModel):
    # Profile/Display
    display_name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    profile_image: Optional[constr(strip_whitespace=True, max_length=500)] = None
    bio: Optional[str] = None
    title: Optional[constr(strip_whitespace=True, max_length=128)] = None

    # Contact
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[constr(strip_whitespace=True, max_length=64)] = None
    contact_preferred: Optional[constr(strip_whitespace=True, max_length=32)] = None

    # Permissions
    can_post_announcements: Optional[bool] = True
    can_manage_events: Optional[bool] = True
    can_moderate_threads: Optional[bool] = True

    # Extra metadata
    extra: Optional[str] = None


# -------------------- Create Schema --------------------
class CommunityAdminProfileCreate(CommunityAdminProfileBase):
    """Create a new community admin profile - requires user_id and community_id"""
    user_id: int
    community_id: int


# -------------------- Update Schema --------------------
class CommunityAdminProfileUpdate(BaseModel):
    """Update an existing community admin profile - all fields optional"""
    display_name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    profile_image: Optional[constr(strip_whitespace=True, max_length=500)] = None
    bio: Optional[str] = None
    title: Optional[constr(strip_whitespace=True, max_length=128)] = None

    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[constr(strip_whitespace=True, max_length=64)] = None
    contact_preferred: Optional[constr(strip_whitespace=True, max_length=32)] = None

    can_post_announcements: Optional[bool] = None
    can_manage_events: Optional[bool] = None
    can_moderate_threads: Optional[bool] = None

    extra: Optional[str] = None


# -------------------- Output Schema --------------------
class CommunityAdminProfileOut(CommunityAdminProfileBase):
    """Response model for community admin profile with all fields"""
    id: int
    user_id: int
    community_id: int

    # Include user info from relationship (optional)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True
