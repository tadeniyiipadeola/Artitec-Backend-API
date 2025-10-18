


from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, constr, conint


# ------------------------------------------------------------
# Related entity schemas
# ------------------------------------------------------------
class CommunityAmenityBase(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    gallery: Optional[List[str]] = None  # list of URLs


class CommunityAmenityCreate(CommunityAmenityBase):
    community_id: Optional[int] = None  # may be injected by route


class CommunityAmenityUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    gallery: Optional[List[str]] = None


class CommunityAmenityOut(CommunityAmenityBase):
    id: int
    community_id: int

    class Config:
        orm_mode = True


class CommunityEventBase(BaseModel):
    date: datetime
    title: constr(strip_whitespace=True, min_length=1, max_length=255)
    subtitle: Optional[constr(strip_whitespace=True, max_length=255)] = None


class CommunityEventCreate(CommunityEventBase):
    community_id: Optional[int] = None


class CommunityEventUpdate(BaseModel):
    date: Optional[datetime] = None
    title: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    subtitle: Optional[constr(strip_whitespace=True, max_length=255)] = None


class CommunityEventOut(CommunityEventBase):
    id: int
    community_id: int

    class Config:
        orm_mode = True


class CommunityBuilderCardBase(BaseModel):
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    subtitle: Optional[constr(strip_whitespace=True, max_length=255)] = None
    followers: Optional[int] = 0
    is_verified: Optional[bool] = False


class CommunityBuilderCardCreate(CommunityBuilderCardBase):
    community_id: Optional[int] = None


class CommunityBuilderCardUpdate(BaseModel):
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    subtitle: Optional[constr(strip_whitespace=True, max_length=255)] = None
    followers: Optional[int] = None
    is_verified: Optional[bool] = None


class CommunityBuilderCardOut(CommunityBuilderCardBase):
    id: int
    community_id: int

    class Config:
        orm_mode = True


class CommunityAdminBase(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    role: Optional[constr(strip_whitespace=True, max_length=128)] = None
    email: Optional[constr(strip_whitespace=True, max_length=255)] = None
    phone: Optional[constr(strip_whitespace=True, max_length=64)] = None


class CommunityAdminCreate(CommunityAdminBase):
    community_id: Optional[int] = None


class CommunityAdminUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    role: Optional[constr(strip_whitespace=True, max_length=128)] = None
    email: Optional[constr(strip_whitespace=True, max_length=255)] = None
    phone: Optional[constr(strip_whitespace=True, max_length=64)] = None


class CommunityAdminOut(CommunityAdminBase):
    id: int
    community_id: int

    class Config:
        orm_mode = True


class CommunityAwardBase(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    year: Optional[int] = None
    issuer: Optional[constr(strip_whitespace=True, max_length=255)] = None
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    note: Optional[str] = None


class CommunityAwardCreate(CommunityAwardBase):
    community_id: Optional[int] = None


class CommunityAwardUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    year: Optional[int] = None
    issuer: Optional[constr(strip_whitespace=True, max_length=255)] = None
    icon: Optional[constr(strip_whitespace=True, max_length=64)] = None
    note: Optional[str] = None


class CommunityAwardOut(CommunityAwardBase):
    id: int
    community_id: int

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
    community_id: Optional[int] = None


class CommunityTopicUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    category: Optional[constr(strip_whitespace=True, max_length=255)] = None
    replies: Optional[int] = None
    last_activity: Optional[constr(strip_whitespace=True, max_length=128)] = None
    is_pinned: Optional[bool] = None
    comments: Optional[List[Any]] = None


class CommunityTopicOut(CommunityTopicBase):
    id: int
    community_id: int

    class Config:
        orm_mode = True


class CommunityPhaseBase(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    lots: Optional[List[Any]] = None  # simplified; can be a dedicated model later
    map_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None


class CommunityPhaseCreate(CommunityPhaseBase):
    community_id: Optional[int] = None


class CommunityPhaseUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    lots: Optional[List[Any]] = None
    map_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None


class CommunityPhaseOut(CommunityPhaseBase):
    id: int
    community_id: int

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
    postal_code: Optional[constr(strip_whitespace=True, max_length=20)] = None

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

    # Media
    intro_video_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None


class CommunityCreate(CommunityBase):
    pass


class CommunityUpdate(BaseModel):
    public_id: Optional[constr(strip_whitespace=True, max_length=64)] = None
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None

    city: Optional[constr(strip_whitespace=True, max_length=255)] = None
    postal_code: Optional[constr(strip_whitespace=True, max_length=20)] = None

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

    intro_video_url: Optional[constr(strip_whitespace=True, max_length=1024)] = None


class CommunityOut(CommunityBase):
    id: int
    public_id: str

    created_at: datetime
    updated_at: datetime

    # Nested relationships (1-to-many)
    amenities: List[CommunityAmenityOut] = []
    events: List[CommunityEventOut] = []
    builder_cards: List[CommunityBuilderCardOut] = []
    admins: List[CommunityAdminOut] = []
    awards: List[CommunityAwardOut] = []
    threads: List[CommunityTopicOut] = []
    phases: List[CommunityPhaseOut] = []

    # Many-to-many builder link exposure by ID (optional; hydrate in route layer)
    builder_ids: List[int] = []

    class Config:
        orm_mode = True
