

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, conint, confloat, constr


# ---------------------------------------------------------------------------
# Shared / Base
# ---------------------------------------------------------------------------
class PropertyBase(BaseModel):
    """Fields common to create/update and read.

    Keep this lean—only fields that belong to the Property entity itself.
    Relationship IDs (builder_id, community_id) live here to allow filtering.
    """

    title: constr(strip_whitespace=True, min_length=3, max_length=140)
    description: Optional[constr(strip_whitespace=True, max_length=5000)] = None

    # Address / location
    address1: constr(strip_whitespace=True, min_length=1, max_length=255)
    address2: Optional[constr(strip_whitespace=True, max_length=255)] = None
    city: constr(strip_whitespace=True, min_length=1, max_length=120)
    state: constr(strip_whitespace=True, min_length=2, max_length=120)
    postal_code: constr(strip_whitespace=True, min_length=3, max_length=20)
    latitude: Optional[confloat(ge=-90, le=90)] = Field(default=None)
    longitude: Optional[confloat(ge=-180, le=180)] = Field(default=None)

    # Specs
    price: confloat(ge=0)
    bedrooms: conint(ge=0)
    bathrooms: confloat(ge=0)
    sqft: Optional[conint(ge=0)] = None
    lot_sqft: Optional[conint(ge=0)] = None
    year_built: Optional[conint(ge=1700, le=datetime.utcnow().year + 1)] = None

    # Property classification
    property_type: Optional[str] = None  # single_family, townhome, condo, etc.
    listing_status: Optional[str] = None  # available, pending, under_contract, sold

    # Structural details
    stories: Optional[int] = None
    garage_spaces: Optional[int] = None

    # Lot characteristics
    corner_lot: Optional[bool] = None
    cul_de_sac: Optional[bool] = None
    lot_backing: Optional[str] = None  # greenbelt, pond, street, etc.
    views: Optional[str] = None

    # School information
    school_district: Optional[str] = None
    elementary_school: Optional[str] = None
    middle_school: Optional[str] = None
    high_school: Optional[str] = None
    school_ratings: Optional[dict] = None

    # Builder-specific information
    model_home: Optional[bool] = None
    quick_move_in: Optional[bool] = None
    construction_stage: Optional[str] = None  # pre_construction, under_construction, completed
    estimated_completion: Optional[str] = None
    builder_plan_name: Optional[str] = None
    builder_series: Optional[str] = None
    elevation_options: Optional[str] = None

    # Interior features
    flooring_types: Optional[str] = None
    countertop_materials: Optional[str] = None
    appliances: Optional[str] = None
    game_room: Optional[bool] = None
    study_office: Optional[bool] = None
    bonus_rooms: Optional[str] = None

    # Outdoor amenities
    pool_type: Optional[str] = None  # private, community, none
    covered_patio: Optional[bool] = None
    outdoor_kitchen: Optional[bool] = None
    landscaping: Optional[str] = None

    # Pricing & market information
    price_per_sqft: Optional[float] = None
    days_on_market: Optional[int] = None
    builder_incentives: Optional[str] = None
    upgrades_included: Optional[str] = None
    upgrades_value: Optional[float] = None

    # HOA & restrictions
    hoa_fee_monthly: Optional[float] = None
    pet_restrictions: Optional[str] = None
    lease_allowed: Optional[bool] = None

    # Energy & utilities
    energy_rating: Optional[str] = None
    internet_providers: Optional[str] = None

    # Tax & financial
    annual_property_tax: Optional[float] = None
    assumable_loan: Optional[bool] = None

    # Media & virtual tours
    virtual_tour_url: Optional[str] = None
    floor_plan_url: Optional[str] = None
    matterport_link: Optional[str] = None

    # Availability & showing
    move_in_date: Optional[str] = None
    showing_instructions: Optional[str] = None

    # Collection metadata
    source_url: Optional[str] = None
    data_confidence: Optional[float] = None

    # Associations / flags
    builder_id: Optional[int] = None
    community_id: Optional[int] = None
    has_pool: bool = False

    # Media links (URLs to images/videos hosted elsewhere)
    media_urls: Optional[List[HttpUrl]] = None


# ---------------------------------------------------------------------------
# Create & Update
# ---------------------------------------------------------------------------
class PropertyCreate(PropertyBase):
    """Incoming payload to create a property.

    Owner is inferred from auth (current user) and not part of this schema.
    `listed_at` and audit timestamps come from the DB default.
    """

    pass


class PropertyUpdate(BaseModel):
    """PATCH-friendly: all fields optional; only provided fields are updated."""

    title: Optional[constr(strip_whitespace=True, min_length=3, max_length=140)] = None
    description: Optional[constr(strip_whitespace=True, max_length=5000)] = None

    address1: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    address2: Optional[constr(strip_whitespace=True, max_length=255)] = None
    city: Optional[constr(strip_whitespace=True, min_length=1, max_length=120)] = None
    state: Optional[constr(strip_whitespace=True, min_length=2, max_length=120)] = None
    postal_code: Optional[constr(strip_whitespace=True, min_length=3, max_length=20)] = None
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None

    price: Optional[confloat(ge=0)] = None
    bedrooms: Optional[conint(ge=0)] = None
    bathrooms: Optional[confloat(ge=0)] = None
    sqft: Optional[conint(ge=0)] = None
    lot_sqft: Optional[conint(ge=0)] = None
    year_built: Optional[conint(ge=1700, le=datetime.utcnow().year + 1)] = None

    # Property classification
    property_type: Optional[str] = None
    listing_status: Optional[str] = None

    # Structural details
    stories: Optional[int] = None
    garage_spaces: Optional[int] = None

    # Lot characteristics
    corner_lot: Optional[bool] = None
    cul_de_sac: Optional[bool] = None
    lot_backing: Optional[str] = None
    views: Optional[str] = None

    # School information
    school_district: Optional[str] = None
    elementary_school: Optional[str] = None
    middle_school: Optional[str] = None
    high_school: Optional[str] = None
    school_ratings: Optional[dict] = None

    # Builder-specific information
    model_home: Optional[bool] = None
    quick_move_in: Optional[bool] = None
    construction_stage: Optional[str] = None
    estimated_completion: Optional[str] = None
    builder_plan_name: Optional[str] = None
    builder_series: Optional[str] = None
    elevation_options: Optional[str] = None

    # Interior features
    flooring_types: Optional[str] = None
    countertop_materials: Optional[str] = None
    appliances: Optional[str] = None
    game_room: Optional[bool] = None
    study_office: Optional[bool] = None
    bonus_rooms: Optional[str] = None

    # Outdoor amenities
    pool_type: Optional[str] = None
    covered_patio: Optional[bool] = None
    outdoor_kitchen: Optional[bool] = None
    landscaping: Optional[str] = None

    # Pricing & market information
    price_per_sqft: Optional[float] = None
    days_on_market: Optional[int] = None
    builder_incentives: Optional[str] = None
    upgrades_included: Optional[str] = None
    upgrades_value: Optional[float] = None

    # HOA & restrictions
    hoa_fee_monthly: Optional[float] = None
    pet_restrictions: Optional[str] = None
    lease_allowed: Optional[bool] = None

    # Energy & utilities
    energy_rating: Optional[str] = None
    internet_providers: Optional[str] = None

    # Tax & financial
    annual_property_tax: Optional[float] = None
    assumable_loan: Optional[bool] = None

    # Media & virtual tours
    virtual_tour_url: Optional[str] = None
    floor_plan_url: Optional[str] = None
    matterport_link: Optional[str] = None

    # Availability & showing
    move_in_date: Optional[str] = None
    showing_instructions: Optional[str] = None

    # Collection metadata
    source_url: Optional[str] = None
    data_confidence: Optional[float] = None

    builder_id: Optional[int] = None
    community_id: Optional[int] = None
    has_pool: Optional[bool] = None

    media_urls: Optional[List[HttpUrl]] = None


# ---------------------------------------------------------------------------
# Out / Read models
# ---------------------------------------------------------------------------
class PropertyOut(PropertyBase):
    """Response model for a property."""

    id: int
    owner_id: int

    created_at: datetime
    updated_at: Optional[datetime] = None
    listed_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# Linked DTOs / Relations payloads
# ---------------------------------------------------------------------------
class LinkedBuilderOut(BaseModel):
    id: int
    name: Optional[str] = None
    builder_id: Optional[str] = None  # builder_profiles.builder_id (e.g., BLD-xxx)

    class Config:
        orm_mode = True


class LinkedCommunityOut(BaseModel):
    id: int
    name: Optional[str] = None
    community_id: Optional[str] = None  # communities.community_id (e.g., CMY-xxx)

    class Config:
        orm_mode = True


class PropertyRelationsOut(BaseModel):
    """Lightweight relations response for a property.

    - primary_builder: from Property.builder_id
    - builders: many-to-many via builder_portfolio
    - community: from Property.community_id
    """

    property_id: int
    primary_builder: Optional[LinkedBuilderOut] = None
    builders: List[LinkedBuilderOut] = []
    community: Optional[LinkedCommunityOut] = None