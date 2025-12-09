"""
Pydantic schemas for Media API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MediaType(str, Enum):
    """Media type enum"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class StorageType(str, Enum):
    """Storage type enum"""
    LOCAL = "LOCAL"
    S3 = "S3"


class ModerationStatus(str, Enum):
    """Moderation status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


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
    entity_field: Optional[EntityField] = Field(None, alias="entityField")
    alt_text: Optional[str] = Field(None, max_length=500, alias="altText")
    caption: Optional[str] = None
    sort_order: Optional[int] = Field(None, alias="sortOrder")
    is_public: Optional[bool] = Field(None, alias="isPublic")
    is_primary: Optional[bool] = Field(None, alias="isPrimary")
    tags: Optional[List[str]] = None
    moderation_status: Optional[ModerationStatus] = Field(None, alias="moderationStatus")

    model_config = ConfigDict(populate_by_name=True)


class BatchUploadRequest(BaseModel):
    """Request for batch media upload"""
    entity_type: EntityType
    entity_id: int
    entity_field: EntityField
    max_files: int = Field(default=20, le=20, description="Maximum 20 files per batch")


# Response Schemas

class MediaOut(BaseModel):
    """Media response schema"""
    id: int
    public_id: str = Field(..., alias="publicId")
    filename: str
    original_filename: str = Field(..., alias="originalFilename")
    media_type: MediaType = Field(..., alias="mediaType")
    content_type: str = Field(..., alias="contentType")
    file_size: int = Field(..., alias="fileSize")

    # Dimensions
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None

    # Duplicate detection
    image_hash: Optional[str] = Field(None, alias="imageHash")

    # Storage configuration
    storage_type: Optional[StorageType] = Field(None, alias="storageType")
    bucket_name: Optional[str] = Field(None, alias="bucketName")

    # URLs - client will use these to display media
    original_url: str = Field(..., alias="originalUrl")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    medium_url: Optional[str] = Field(None, alias="mediumUrl")
    large_url: Optional[str] = Field(None, alias="largeUrl")
    video_processed_url: Optional[str] = Field(None, alias="videoProcessedUrl")

    # Entity relationship
    entity_type: str = Field(..., alias="entityType")
    entity_id: int = Field(..., alias="entityId")
    entity_field: Optional[str] = Field(None, alias="entityField")
    entity_profile_id: Optional[str] = Field(None, alias="entityProfileId")  # e.g., "CMY-1763002158-W1Y12N" or "BLD-..."

    # Metadata
    alt_text: Optional[str] = Field(None, alias="altText")
    caption: Optional[str] = None
    sort_order: Optional[int] = Field(0, alias="sortOrder")
    is_primary: Optional[bool] = Field(False, alias="isPrimary")
    source_url: Optional[str] = Field(None, alias="sourceUrl")  # URL of webpage where media was scraped from
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    # Ownership
    uploaded_by: str = Field(..., alias="uploadedBy")
    is_public: bool = Field(..., alias="isPublic")
    is_approved: bool = Field(True, alias="isApproved")  # False for scraped media pending approval
    moderation_status: Optional[ModerationStatus] = Field(None, alias="moderationStatus")

    # Timestamps
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,  # Allow enum values from different enum classes
        populate_by_name=True,  # Allow both snake_case and camelCase field names
    )


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
