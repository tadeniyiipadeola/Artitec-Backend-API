

"""Pydantic schemas for Builder Profiles (Pydantic v2)

Placed in `schema/builder.py` per project preference to keep schemas in a dedicated
module separate from routes and SQLAlchemy models.
"""
from __future__ import annotations

from datetime import datetime
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

    # Business details
    founded_year: Optional[int] = None  # Year company was founded
    employee_count: Optional[int] = None  # Number of employees
    price_range_min: Optional[int] = None  # Minimum home price
    price_range_max: Optional[int] = None  # Maximum home price
    headquarters_address: Optional[str] = None  # Main office address
    sales_office_address: Optional[str] = None  # Sales office address
    mission: Optional[str] = None  # Company mission statement
    service_areas: Optional[List[str]] = None  # Geographic service areas

    # Aggregated credentials (computed from BuilderCredential table)
    licenses: Optional[List[str]] = None  # List of license names
    certifications: Optional[List[str]] = None  # List of certification names
    memberships: Optional[List[str]] = None  # List of membership names


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Out model
# ------------------------------------------------------------
class BuilderProfileOut(BuilderProfileBase):
    id: int
    builder_id: str  # builder_profiles.builder_id (e.g., BLD-1699564234-X3P8Q1)
    user_id: str  # FK to users.user_id (string, e.g., USR-xxx)

    # Timestamps - Pydantic v2 automatically serializes datetime to ISO string in JSON
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Expanded relationships (optional, loaded via includes)
    properties: Optional[List[PropertyRef]] = None
    communities: Optional[List[CommunityRef]] = None

    # Enable ORM mode
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# BuilderAward schemas
# ------------------------------------------------------------
class BuilderAwardBase(BaseModel):
    title: str
    awarded_by: Optional[str] = None
    year: Optional[int] = None

class BuilderAwardCreate(BuilderAwardBase):
    pass

class BuilderAwardUpdate(BaseModel):
    title: Optional[str] = None
    awarded_by: Optional[str] = None
    year: Optional[int] = None

class BuilderAwardOut(BuilderAwardBase):
    id: int
    builder_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# BuilderHomePlan schemas
# ------------------------------------------------------------
class BuilderHomePlanBase(BaseModel):
    name: str
    series: str
    sqft: conint(gt=0)
    beds: conint(ge=0)
    baths: confloat(ge=0)
    stories: conint(gt=0)
    starting_price: str  # Stored as string (e.g., "450000.00")
    description: Optional[str] = None
    image_url: Optional[str] = None

class BuilderHomePlanCreate(BuilderHomePlanBase):
    pass

class BuilderHomePlanUpdate(BaseModel):
    name: Optional[str] = None
    series: Optional[str] = None
    sqft: Optional[conint(gt=0)] = None
    beds: Optional[conint(ge=0)] = None
    baths: Optional[confloat(ge=0)] = None
    stories: Optional[conint(gt=0)] = None
    starting_price: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class BuilderHomePlanOut(BuilderHomePlanBase):
    id: int
    builder_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# BuilderCredential schemas
# ------------------------------------------------------------
class BuilderCredentialBase(BaseModel):
    name: str
    credential_type: str  # "license", "certification", or "membership"

class BuilderCredentialCreate(BuilderCredentialBase):
    pass

class BuilderCredentialUpdate(BaseModel):
    name: Optional[str] = None
    credential_type: Optional[str] = None

class BuilderCredentialOut(BuilderCredentialBase):
    id: int
    builder_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)