

"""Pydantic schemas for Builder Profiles (Pydantic v2)

Placed in `schema/builder.py` per project preference to keep schemas in a dedicated
module separate from routes and SQLAlchemy models.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl, conint, confloat


# ------------------------------------------------------------
# Shared fields
# ------------------------------------------------------------
class BuilderProfileBase(BaseModel):
    # Identity/description
    license_number: Optional[str] = None
    company_name: Optional[str] = None
    about: Optional[str] = None
    notes: Optional[str] = None

    # JSON-like fields represented as Python lists for convenience
    specialties: Optional[List[str]] = None  # e.g., ["Custom Homes", "Renovation"]
    service_areas: Optional[List[str]] = None  # e.g., ["Houston, TX", "Kingwood, TX"]

    years_in_business: Optional[conint(ge=0, le=200)] = None
    rating_avg: Optional[confloat(ge=0, le=5)] = None
    rating_count: Optional[conint(ge=0)] = 0

    # Contact & presence
    website_url: Optional[HttpUrl] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    # Addressing (denormalized for convenience)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None

    # Media
    logo_url: Optional[HttpUrl] = None

    # Relationships (IDs for simple updates; expanded objects in Out model)
    property_ids: Optional[List[int]] = None  # portfolio
    community_ids: Optional[List[int]] = None  # active communities


# ------------------------------------------------------------
# Create / Update models
# ------------------------------------------------------------
class BuilderProfileCreate(BuilderProfileBase):
    org_id: int


class BuilderProfileUpdate(BuilderProfileBase):
    # All fields optional for PATCH/PUT semantics
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
# Out model
# ------------------------------------------------------------
class BuilderProfileOut(BuilderProfileBase):
    org_id: int

    # Social / follower metrics (server-derived)
    followers_count: int = 0
    is_following: Optional[bool] = None  # whether the current auth user follows this builder

    # Expanded relationships
    properties: Optional[List[PropertyRef]] = None
    communities: Optional[List[CommunityRef]] = None

    # Enable ORM mode
    model_config = ConfigDict(from_attributes=True)