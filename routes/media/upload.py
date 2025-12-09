"""
Media upload endpoints - Handle file uploads and processing
"""

import uuid
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from config.db import get_db
from model.media import Media, MediaType
from schema.media import MediaOut, MediaUploadResponse, EntityType, EntityField
from src.id_generator import generate_public_id
from config.security import get_current_user
from src.storage import get_storage_backend
from src.media_processing import ImageProcessor, VideoProcessor
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Get storage backend (configured via environment)
storage = get_storage_backend()


# Helper function to get entity profile ID
def get_entity_profile_id(db: Session, entity_type: str, entity_id: int) -> Optional[str]:
    """
    Get the profile ID (community_id, builder_id, etc.) for an entity.

    Args:
        db: Database session
        entity_type: Type of entity (community, builder, user, etc.)
        entity_id: Database integer ID of the entity

    Returns:
        The profile ID string (e.g., "CMY-...", "BLD-...") or None
    """
    try:
        if entity_type == "community":
            from model.profiles.community import Community
            community = db.query(Community).filter(Community.id == entity_id).first()
            return community.community_id if community else None

        elif entity_type == "builder":
            from model.profiles.builder import BuilderProfile
            builder = db.query(BuilderProfile).filter(BuilderProfile.id == entity_id).first()
            return builder.builder_id if builder else None

        elif entity_type == "user":
            from model.user import Users
            user = db.query(Users).filter(Users.id == entity_id).first()
            return user.user_id if user else None

        # Add more entity types as needed
        else:
            return None
    except Exception as e:
        logger.warning(f"Error fetching profile ID for {entity_type}/{entity_id}: {e}")
        return None


# Helper to convert relative URL to full URL
def make_full_url(url: Optional[str], base_url: str) -> Optional[str]:
    """
    Convert relative URL to full URL.
    Uses S3/MinIO public URL if STORAGE_TYPE=s3, otherwise uses base URL.

    Args:
        url: The URL from database (could be relative or full)
        base_url: The base URL from environment (e.g., http://localhost:8000)

    Returns:
        Full URL or None
    """
    if not url:
        return None

    # If already a full URL (starts with http:// or https://), return as-is
    if url.startswith(('http://', 'https://')):
        return url

    # Check storage type from environment
    storage_type = os.getenv("STORAGE_TYPE", "local").upper()

    if storage_type == "S3":
        # Use S3 public base URL for MinIO/S3 storage
        s3_public_base_url = os.getenv("S3_PUBLIC_BASE_URL")
        if s3_public_base_url:
            return f"{s3_public_base_url}/{url}"
        # Fallback if S3_PUBLIC_BASE_URL not set
        s3_endpoint = os.getenv("S3_ENDPOINT_URL")
        s3_bucket = os.getenv("S3_BUCKET_NAME")
        if s3_endpoint and s3_bucket:
            return f"{s3_endpoint}/{s3_bucket}/{url}"

    # For local storage, prepend base URL and /uploads/
    return f"{base_url}/uploads/{url}"


# Helper to convert Media to MediaOut with profile ID
def media_to_out(db: Session, media: Media) -> MediaOut:
    """Convert Media ORM object to MediaOut schema with entity_profile_id populated"""
    # Get base URL from environment for converting old relative URLs
    base_url = os.getenv("BASE_URL", "http://localhost:8000")

    media_dict = {
        "id": media.id,
        "public_id": media.public_id,
        "filename": media.filename,
        "original_filename": media.original_filename,
        "media_type": media.media_type,
        "content_type": media.content_type,
        "file_size": media.file_size,
        "width": media.width,
        "height": media.height,
        "duration": media.duration,
        "original_url": make_full_url(media.original_url, base_url),
        "thumbnail_url": make_full_url(media.thumbnail_url, base_url),
        "medium_url": make_full_url(media.medium_url, base_url),
        "large_url": make_full_url(media.large_url, base_url),
        "video_processed_url": make_full_url(media.video_processed_url, base_url),
        "entity_type": media.entity_type,
        "entity_id": media.entity_id,
        "entity_field": media.entity_field,
        "entity_profile_id": get_entity_profile_id(db, media.entity_type, media.entity_id),
        "alt_text": media.alt_text,
        "caption": media.caption,
        "sort_order": media.sort_order,
        "source_url": media.source_url,
        "uploaded_by": media.uploaded_by,
        "is_public": media.is_public,
        "is_approved": media.is_approved,
        "created_at": media.created_at,
        "updated_at": media.updated_at,
    }
    return MediaOut(**media_dict)


# Helper function to generate unique filename
def generate_filename(original_filename: str) -> str:
    """Generate unique filename preserving extension"""
    ext = Path(original_filename).suffix.lower()
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{ext}"


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    entity_type: EntityType = Form(...),
    entity_id: int = Form(...),
    entity_field: Optional[EntityField] = Form(None),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(0),
    is_public: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a photo or video.
    Automatically processes images (generates thumbnails, resizes).
    Supports: property photos, community images, avatars, videos, posts/reels.
    """
    logger.info(f"📤 Media upload started: user={current_user['public_id']}, file={file.filename}, entity={entity_type}/{entity_id}")

    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Determine media type
        is_image = ImageProcessor.is_supported(file.filename)
        is_video = VideoProcessor.is_supported(file.filename)

        if not is_image and not is_video:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: images (jpg, png, gif, webp) and videos (mp4, mov, avi)"
            )

        media_type = MediaType.IMAGE if is_image else MediaType.VIDEO

        # Read file into memory
        file_data = await file.read()
        file_size = len(file_data)
        content_type = file.content_type or "application/octet-stream"

        # Generate unique filename
        unique_filename = generate_filename(file.filename)
        base_name = Path(unique_filename).stem

        # Get profile ID for organized storage
        profile_id = get_entity_profile_id(db, entity_type.value, entity_id)
        entity_field_value = entity_field.value if entity_field else None

        # Initialize URLs
        original_url = None
        thumbnail_url = None
        medium_url = None
        large_url = None
        video_processed_url = None
        width, height, duration = None, None, None

        # Process based on type
        if is_image:
            logger.info("🖼️  Processing image...")
            import io

            # Get dimensions
            width, height = ImageProcessor.get_image_dimensions(io.BytesIO(file_data))

            # Process image (generate all sizes)
            processed = ImageProcessor.process_image(io.BytesIO(file_data), base_name)

            # Upload original with organized path
            storage_path, original_url = await storage.save(
                processed['original'],
                unique_filename,
                content_type,
                profile_id=profile_id,
                entity_field=entity_field_value
            )

            # Upload thumbnail
            if processed['thumbnail']:
                thumb_filename = f"{base_name}_thumb.jpg"
                _, thumbnail_url = await storage.save(
                    processed['thumbnail'],
                    thumb_filename,
                    "image/jpeg",
                    profile_id=profile_id,
                    entity_field=entity_field_value
                )

            # Upload medium
            if processed['medium']:
                medium_filename = f"{base_name}_medium.jpg"
                _, medium_url = await storage.save(
                    processed['medium'],
                    medium_filename,
                    "image/jpeg",
                    profile_id=profile_id,
                    entity_field=entity_field_value
                )

            # Upload large
            if processed['large']:
                large_filename = f"{base_name}_large.jpg"
                _, large_url = await storage.save(
                    processed['large'],
                    large_filename,
                    "image/jpeg",
                    profile_id=profile_id,
                    entity_field=entity_field_value
                )

        elif is_video:
            logger.info("🎥 Processing video...")
            import tempfile

            # Save video to temp file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_video:
                temp_video.write(file_data)
                temp_video_path = temp_video.name

            try:
                # Get video metadata
                metadata = VideoProcessor.get_video_metadata(temp_video_path)
                width = metadata.get('width')
                height = metadata.get('height')
                duration = metadata.get('duration')

                # Upload original video with organized path
                import io
                storage_path, original_url = await storage.save(
                    io.BytesIO(file_data),
                    unique_filename,
                    content_type,
                    profile_id=profile_id,
                    entity_field=entity_field_value
                )

                # Generate video thumbnail
                thumb_filename = f"{base_name}_thumb.jpg"
                temp_thumb_path = f"/tmp/{thumb_filename}"

                if VideoProcessor.generate_video_thumbnail(temp_video_path, temp_thumb_path):
                    with open(temp_thumb_path, 'rb') as thumb_file:
                        _, thumbnail_url = await storage.save(
                            thumb_file,
                            thumb_filename,
                            "image/jpeg",
                            profile_id=profile_id,
                            entity_field=entity_field_value
                        )
                    os.remove(temp_thumb_path)

                # TODO: Optionally compress video in background task
                # For now, we'll just use the original

            finally:
                # Clean up temp file
                os.remove(temp_video_path)

        # Create media record in database
        media = Media(
            public_id=generate_public_id("media"),
            filename=unique_filename,
            original_filename=file.filename,
            media_type=media_type,
            content_type=content_type,
            file_size=file_size,
            width=width,
            height=height,
            duration=duration,
            storage_path=storage_path,
            original_url=original_url,
            thumbnail_url=thumbnail_url,
            medium_url=medium_url,
            large_url=large_url,
            video_processed_url=video_processed_url,
            entity_type=entity_type.value,
            entity_id=entity_id,
            entity_field=entity_field.value if entity_field else None,
            alt_text=alt_text,
            caption=caption,
            sort_order=sort_order,
            uploaded_by=current_user['public_id'],
            is_public=is_public
        )

        db.add(media)
        db.commit()
        db.refresh(media)

        logger.info(f"✅ Media uploaded successfully: id={media.id}, public_id={media.public_id}")

        return MediaUploadResponse(
            media=media_to_out(db, media),
            message="Media uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading media: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading media: {str(e)}")
