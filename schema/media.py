"""
Pydantic schemas for Media API.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class MediaType(str, Enum):
    """Media type enum"""
    IMAGE = "image"
    VIDEO = "video"


class EntityType(str, Enum):
    """Supported entity types for media attachment"""
    PROPERTY = "property"
    COMMUNITY = "community"
    USER = "user"
    POST = "post"
    AMENITY = "amenity"
    EVENT = "event"
    BUILDER = "builder"
    SALES_REP = "sales_rep"
    COMMUNITY_ADMIN = "community_admin"


class EntityField(str, Enum):
    """Common entity fields where media can be attached"""
    AVATAR = "avatar"
    COVER = "cover"
    GALLERY = "gallery"
    VIDEO_INTRO = "video_intro"
    THUMBNAIL = "thumbnail"


# Request Schemas

class MediaUploadRequest(BaseModel):
    """Request for media upload metadata"""
    entity_type: EntityType
    entity_id: int
    entity_field: Optional[EntityField] = None
    alt_text: Optional[str] = Field(None, max_length=500)
    caption: Optional[str] = None
    sort_order: Optional[int] = 0
    is_public: bool = True


class MediaUpdateRequest(BaseModel):
    """Request to update media metadata"""
    alt_text: Optional[str] = Field(None, max_length=500)
    caption: Optional[str] = None
    sort_order: Optional[int] = None
    is_public: Optional[bool] = None


# Response Schemas

class MediaOut(BaseModel):
    """Media response schema"""
    id: int
    public_id: str
    filename: str
    original_filename: str
    media_type: MediaType
    content_type: str
    file_size: int

    # Dimensions
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None

    # URLs - client will use these to display media
    original_url: str
    thumbnail_url: Optional[str] = None
    medium_url: Optional[str] = None
    large_url: Optional[str] = None
    video_processed_url: Optional[str] = None

    # Entity relationship
    entity_type: str
    entity_id: int
    entity_field: Optional[str] = None

    # Metadata
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    sort_order: Optional[int] = 0

    # Ownership
    uploaded_by: str
    is_public: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MediaListOut(BaseModel):
    """Response for listing media"""
    items: list[MediaOut]
    total: int


class MediaUploadResponse(BaseModel):
    """Response after successful upload"""
    media: MediaOut
    message: str = "Media uploaded successfully"


class MediaDeleteResponse(BaseModel):
    """Response after successful deletion"""
    message: str = "Media deleted successfully"
    deleted_id: int
