

"""Pydantic schemas for Builder Profiles (Pydantic v2)

Placed in `schema/builder.py` per project preference to keep schemas in a dedicated
module separate from routes and SQLAlchemy models.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl, conint, confloat


# ------------------------------------------------------------
# Shared fields (matching model/profiles/builder.py)
# ------------------------------------------------------------
class BuilderProfileBase(BaseModel):
    # Core fields
    name: str  # Company/builder name (required)
    website: Optional[str] = None
    specialties: Optional[List[str]] = None  # e.g., ["Custom Homes", "Townhomes"]
    rating: Optional[confloat(ge=0, le=5)] = None
    communities_served: Optional[List[str]] = None  # e.g., ["Oak Meadows", "Pine Ridge"]

    # Optional extended fields
    about: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None  # Street address
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    verified: Optional[int] = 0  # 0 = not verified, 1 = verified

    # Profile metadata
    title: Optional[str] = None  # e.g., "Owner", "Regional Manager"
    bio: Optional[str] = None
    socials: Optional[dict] = None  # {"linkedin": "...", "x": "..."}


# ------------------------------------------------------------
# Create / Update models
# ------------------------------------------------------------
class BuilderProfileCreate(BuilderProfileBase):
    # user_id will be resolved from URL path parameter (public_id) in the route
    # No need to pass it in the payload
    pass


class BuilderProfileUpdate(BuilderProfileBase):
    # All fields optional for PATCH/PUT semantics
    name: Optional[str] = None  # Make name optional for updates
    pass


# ------------------------------------------------------------
# Lightweight nested refs for Out model
# ------------------------------------------------------------
class PropertyRef(BaseModel):
    id: int
    title: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CommunityRef(BaseModel):
    id: int
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# SalesRep schemas
# ------------------------------------------------------------
class SalesRepBase(BaseModel):
    first_name: str
    last_name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    region: Optional[str] = None
    office_address: Optional[str] = None
    verified: Optional[bool] = False
    builder_id: Optional[int] = None
    community_id: Optional[int] = None

class SalesRepCreate(SalesRepBase):
    builder_id: int

class SalesRepUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    region: Optional[str] = None
    office_address: Optional[str] = None
    verified: Optional[bool] = None
    builder_id: Optional[int] = None
    community_id: Optional[int] = None

class SalesRepOut(SalesRepBase):
    id: int
    builder_id: int
    community_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Out model
# ------------------------------------------------------------
class BuilderProfileOut(BuilderProfileBase):
    id: int
    build_id: str  # e.g., "B_329_XXX_XXX_XXX_XXX"
    user_id: int

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Expanded relationships (optional, loaded via includes)
    properties: Optional[List[PropertyRef]] = None
    communities: Optional[List[CommunityRef]] = None

    # Enable ORM mode
    model_config = ConfigDict(from_attributes=True)