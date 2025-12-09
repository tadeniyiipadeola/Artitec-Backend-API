"""
Media model for storing photos and videos.
Supports property photos, community images, profile avatars, videos, posts/reels.
"""

from sqlalchemy import Column, Integer, String, Text, BigInteger, Boolean, DateTime, Enum as SQLEnum, Index, JSON
from sqlalchemy.sql import func
from model.base import Base
import enum


class MediaType(enum.Enum):
    """Media type enum"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class StorageType(enum.Enum):
    """Storage type enum"""
    LOCAL = "LOCAL"
    S3 = "S3"


class ModerationStatus(enum.Enum):
    """Moderation status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class Media(Base):
    """
    Media table for storing all photos and videos.
    Uses polymorphic pattern (entity_type, entity_id) to associate with different entities.
    """
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(String(30), nullable=False, unique=True, comment="Public-facing ID")

    # File information
    filename = Column(String(255), nullable=False, comment="Generated unique filename")
    original_filename = Column(String(255), nullable=False, comment="Original uploaded filename")
    media_type = Column(SQLEnum(MediaType), nullable=False)
    content_type = Column(String(100), nullable=False, comment="MIME type: image/jpeg, video/mp4, etc.")
    file_size = Column(BigInteger, nullable=False, comment="File size in bytes")

    # Dimensions (for images and videos)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True, comment="Duration in seconds for videos")

    # Duplicate detection
    image_hash = Column(String(64), nullable=True, comment="Perceptual hash for duplicate detection")

    # Storage configuration
    storage_type = Column(SQLEnum(StorageType), nullable=False, default=StorageType.LOCAL, comment="Storage backend: local or s3")
    bucket_name = Column(String(100), nullable=True, comment="S3/MinIO bucket name if using S3 storage")

    # Storage URLs - flexible for local filesystem or S3
    storage_path = Column(Text, nullable=False, comment="Base storage path or S3 bucket key")
    original_url = Column(Text, nullable=False, comment="URL to access original file")
    thumbnail_url = Column(Text, nullable=True, comment="URL to thumbnail (150x150)")
    medium_url = Column(Text, nullable=True, comment="URL to medium size (800px wide)")
    large_url = Column(Text, nullable=True, comment="URL to large size (1600px wide)")
    video_processed_url = Column(Text, nullable=True, comment="Processed/compressed video URL")

    # Polymorphic relationship - associate with any entity
    entity_type = Column(String(50), nullable=False, comment="property, community, user, post, amenity, event")
    entity_id = Column(Integer, nullable=False, comment="ID of the related entity")
    entity_field = Column(String(50), nullable=True, comment="Specific field: avatar, gallery, cover, video_intro")

    # Metadata
    alt_text = Column(String(500), nullable=True, comment="Accessibility description")
    caption = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=True, default=0, comment="Order within gallery")
    is_primary = Column(Boolean, nullable=False, default=False, comment="Primary/featured media for entity")
    source_url = Column(Text, nullable=True, comment="Source URL if scraped from a website")
    tags = Column(JSON, nullable=True, comment="Searchable tags as JSON array")
    file_metadata = Column('metadata', JSON, nullable=True, comment="EXIF data, processing info, etc. as JSON")

    # Ownership and security
    uploaded_by = Column(String(30), nullable=False, comment="User public_id who uploaded this")
    is_public = Column(Boolean, nullable=False, default=True, comment="Whether publicly accessible")
    is_approved = Column(Boolean, nullable=False, default=True, comment="Whether approved to keep (scraped media starts as False)")
    moderation_status = Column(SQLEnum(ModerationStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ModerationStatus.APPROVED, comment="Moderation status for content review")

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_media_entity', 'entity_type', 'entity_id'),
        Index('idx_media_uploaded_by', 'uploaded_by'),
        Index('idx_media_created_at', 'created_at'),
        Index('idx_media_public_id', 'public_id'),
    )

    def __repr__(self):
        return f"<Media(id={self.id}, public_id={self.public_id}, type={self.media_type.value}, entity={self.entity_type}/{self.entity_id})>"
