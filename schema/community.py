


from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, constr, conint, Field

# Pydantic v2/v1 compatibility for from_attributes/orm_mode
try:
    from pydantic import ConfigDict  # Pydantic v2
    _HAS_V2 = True
except Exception:  # Pydantic v1 fallback
    _HAS_V2 = False


# ------------------------------------------------------------
# Related entity schemas
# ------------------------------------------------------------
class CommunityAmenityBase(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    gallery: Optional[List[str]] = None  # list of URLs


class CommunityAmenityCreate(CommunityAmenityBase):
    community_id: Optional[str] = None  # may be injected by route (public community_id)


class CommunityAmenityUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    gallery: Optional[List[str]] = None


class CommunityAmenityOut(CommunityAmenityBase):
    id: int
    community_id: str  # Public community ID (CMY-XXX)

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CommunityEventBase(BaseModel):
    title: constr(strip_whitespace=True, min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    start_at: datetime
    end_at: Optional[datetime] = None
    is_public: Optional[bool] = True


class CommunityEventCreate(CommunityEventBase):
    community_id: Optional[str] = None  # Public community ID


class CommunityEventUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    description: Optional[str] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    is_public: Optional[bool] = None


class CommunityEventOut(CommunityEventBase):
    id: int
    community_id: str  # Public community ID (CMY-XXX)
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CommunityBuilderCardBase(BaseModel):
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    subtitle: Optional[constr(strip_whitespace=True, max_length=255)] = None
    followers: Optional[int] = 0
    is_verified: Optional[bool] = False


class CommunityBuilderCardCreate(CommunityBuilderCardBase):
    community_id: Optional[str] = None  # Public community ID


class CommunityBuilderCardUpdate(BaseModel):
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    subtitle: Optional[constr(strip_whitespace=True, max_length=255)] = None
    followers: Optional[int] = None
    is_verified: Optional[bool] = None


class CommunityBuilderCardOut(CommunityBuilderCardBase):
    id: int
    community_id: str  # Public community ID (CMY-XXX)

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CommunityAdminBase(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    role: Optional[constr(strip_whitespace=True, max_length=128)] = None
    email: Optional[constr(strip_whitespace=True, max_length=255)] = None
    phone: Optional[constr(strip_whitespace=True, max_length=64)] = None


class CommunityAdminCreate(CommunityAdminBase):
    community_id: Optional[str] = None  # Public community ID


class CommunityAdminUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    role: Optional[constr(strip_whitespace=True, max_length=128)] = None
    email: Optional[constr(strip_whitespace=True, max_length=255)] = None
    phone: Optional[constr(strip_whitespace=True, max_length=64)] = None


class CommunityAdminOut(CommunityAdminBase):
    id: int
    community_id: str  # Public community ID (CMY-XXX)

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CommunityAwardBase(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    year: Optional[int] = None
    issuer: Optional[constr(strip_whitespace=True, max_length=255)] = None
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    note: Optional[str] = None


class CommunityAwardCreate(CommunityAwardBase):
    community_id: Optional[str] = None  # Public community ID


class CommunityAwardUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    year: Optional[int] = None
    issuer: Optional[constr(strip_whitespace=True, max_length=255)] = None
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    note: Optional[str] = None


class CommunityAwardOut(CommunityAwardBase):
    id: int
    community_id: str  # Public community ID (CMY-XXX)

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CommunityTopicBase(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    category: Optional[constr(strip_whitespace=True, max_length=255)] = None
    replies: Optional[int] = 0
    last_activity: Optional[constr(strip_whitespace=True, max_length=128)] = None
    is_pinned: Optional[bool] = False
    comments: Optional[List[Any]] = None  # list of dicts (author, text, timestamp)


class CommunityTopicCreate(CommunityTopicBase):
    community_id: Optional[str] = None  # Public community ID


class CommunityTopicUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    category: Optional[constr(strip_whitespace=True, max_length=255)] = None
    replies: Optional[int] = None
    last_activity: Optional[constr(strip_whitespace=True, max_length=128)] = None
    is_pinned: Optional[bool] = None
    comments: Optional[List[Any]] = None


class CommunityTopicOut(CommunityTopicBase):
    id: int
    community_id: str  # Public community ID (CMY-XXX)

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class CommunityPhaseBase(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    lots: Optional[List[Any]] = None  # simplified; can be a dedicated model later
    map_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None


class CommunityPhaseCreate(CommunityPhaseBase):
    community_id: Optional[str] = None  # Public community ID


class CommunityPhaseUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    lots: Optional[List[Any]] = None
    map_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None


class CommunityPhaseOut(CommunityPhaseBase):
    id: int
    community_id: str  # Public community ID (CMY-XXX)

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


# ------------------------------------------------------------
# Community schemas (root)
# ------------------------------------------------------------
class CommunityBase(BaseModel):
    # Identity
    public_id: Optional[constr(strip_whitespace=True, max_length=64)] = None
    name: constr(strip_whitespace=True, min_length=1, max_length=255)

    # Location
    city: Optional[constr(strip_whitespace=True, max_length=255)] = None
    state: Optional[constr(strip_whitespace=True, max_length=64)] = None
    postal_code: Optional[constr(strip_whitespace=True, max_length=20)] = None
    latitude: Optional[float] = None  # Latitude coordinate for mapping
    longitude: Optional[float] = None  # Longitude coordinate for mapping

    # Contact Information
    phone: Optional[constr(strip_whitespace=True, max_length=32)] = None
    email: Optional[constr(strip_whitespace=True, max_length=255)] = None
    sales_office_address: Optional[constr(strip_whitespace=True, max_length=512)] = None

    # Schools
    school_district: Optional[constr(strip_whitespace=True, max_length=255)] = None
    elementary_school: Optional[constr(strip_whitespace=True, max_length=255)] = None
    middle_school: Optional[constr(strip_whitespace=True, max_length=255)] = None
    high_school: Optional[constr(strip_whitespace=True, max_length=255)] = None

    # HOA Management (existing fields from database)
    hoa_management_company: Optional[constr(strip_whitespace=True, max_length=255)] = None
    hoa_contact_phone: Optional[constr(strip_whitespace=True, max_length=20)] = None
    hoa_contact_email: Optional[constr(strip_whitespace=True, max_length=255)] = None

    # Finance / Meta
    community_dues: Optional[constr(strip_whitespace=True, max_length=64)] = None
    tax_rate: Optional[constr(strip_whitespace=True, max_length=32)] = None
    monthly_fee: Optional[constr(strip_whitespace=True, max_length=64)] = None

    followers: Optional[int] = 0
    about: Optional[str] = None
    is_verified: bool = False

    # Stats
    homes: Optional[int] = 0
    residents: Optional[int] = 0
    founded_year: Optional[int] = None
    member_count: Optional[int] = 0

    # Development
    development_stage: Optional[constr(strip_whitespace=True, max_length=64)] = None
    development_start_year: Optional[int] = None
    is_master_planned: Optional[bool] = False
    enterprise_number_hoa: Optional[constr(strip_whitespace=True, max_length=255)] = None
    developer_name: Optional[constr(strip_whitespace=True, max_length=255)] = None

    # Reviews
    rating: Optional[float] = None
    review_count: Optional[int] = 0

    # Media
    intro_video_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None
    community_website_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None


class CommunityCreate(CommunityBase):
    # Optional: Accept list of amenity names during creation
    amenity_names: Optional[List[str]] = Field(default_factory=list, description="List of amenity names to create (e.g., ['Pool', 'Fitness Center', 'Dog Park'])")


class CommunityUpdate(BaseModel):
    public_id: Optional[constr(strip_whitespace=True, max_length=64)] = None
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None

    city: Optional[constr(strip_whitespace=True, max_length=255)] = None
    state: Optional[constr(strip_whitespace=True, max_length=64)] = None
    postal_code: Optional[constr(strip_whitespace=True, max_length=20)] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Contact Information
    phone: Optional[constr(strip_whitespace=True, max_length=32)] = None
    email: Optional[constr(strip_whitespace=True, max_length=255)] = None
    sales_office_address: Optional[constr(strip_whitespace=True, max_length=512)] = None

    # Schools
    school_district: Optional[constr(strip_whitespace=True, max_length=255)] = None
    elementary_school: Optional[constr(strip_whitespace=True, max_length=255)] = None
    middle_school: Optional[constr(strip_whitespace=True, max_length=255)] = None
    high_school: Optional[constr(strip_whitespace=True, max_length=255)] = None

    # HOA Management
    hoa_management_company: Optional[constr(strip_whitespace=True, max_length=255)] = None
    hoa_contact_phone: Optional[constr(strip_whitespace=True, max_length=20)] = None
    hoa_contact_email: Optional[constr(strip_whitespace=True, max_length=255)] = None

    community_dues: Optional[constr(strip_whitespace=True, max_length=64)] = None
    tax_rate: Optional[constr(strip_whitespace=True, max_length=32)] = None
    monthly_fee: Optional[constr(strip_whitespace=True, max_length=64)] = None

    followers: Optional[int] = None
    about: Optional[str] = None
    is_verified: Optional[bool] = None

    homes: Optional[int] = None
    residents: Optional[int] = None
    founded_year: Optional[int] = None
    member_count: Optional[int] = None

    development_stage: Optional[constr(strip_whitespace=True, max_length=64)] = None
    development_start_year: Optional[int] = None
    is_master_planned: Optional[bool] = None
    enterprise_number_hoa: Optional[constr(strip_whitespace=True, max_length=255)] = None
    developer_name: Optional[constr(strip_whitespace=True, max_length=255)] = None

    # Reviews
    rating: Optional[float] = None
    review_count: Optional[int] = None

    intro_video_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None
    community_website_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None

    # Optional: Replace all amenities with new list
    amenity_names: Optional[List[str]] = Field(None, description="If provided, replaces all existing amenities with this list")


class CommunityOut(CommunityBase):
    id: int
    community_id: str  # communities.community_id (e.g., CMY-1699564234-Z5R7N4)
    user_id: Optional[str] = None  # FK to users.user_id (string, e.g., USR-xxx)

    created_at: datetime
    updated_at: datetime

    # Media URLs (populated from media table)
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    cover_url: Optional[str] = Field(None, alias="coverUrl")

    # Nested relationships (1-to-many)
    amenities: List[CommunityAmenityOut] = Field(default_factory=list)
    events: List[CommunityEventOut] = Field(default_factory=list)
    builder_cards: List[CommunityBuilderCardOut] = Field(default_factory=list)
    admins: List[CommunityAdminOut] = Field(default_factory=list)
    awards: List[CommunityAwardOut] = Field(default_factory=list)
    threads: List[CommunityTopicOut] = Field(default_factory=list)
    phases: List[CommunityPhaseOut] = Field(default_factory=list)

    # Many-to-many builder link exposure by ID (optional; hydrate in route layer)
    builder_ids: List[int] = Field(default_factory=list)

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    else:
        class Config:
            orm_mode = True
            allow_population_by_field_name = True
