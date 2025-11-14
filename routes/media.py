"""
Media upload and management endpoints.
Handles photos, videos, and file management for all entities.
"""

import uuid
import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from config.db import get_db
from model.media import Media, MediaType
from schema.media import (
    MediaOut, MediaListOut, MediaUploadResponse, MediaDeleteResponse,
    EntityType, EntityField
)
from src.id_generator import generate_public_id
from config.security import get_current_user
from src.storage import get_storage_backend
from src.media_processing import ImageProcessor, VideoProcessor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/media", tags=["Media"])

# Get storage backend (configured via environment)
storage = get_storage_backend()


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

            # Upload original
            storage_path, original_url = await storage.save(
                processed['original'],
                unique_filename,
                content_type
            )

            # Upload thumbnail
            if processed['thumbnail']:
                thumb_filename = f"{base_name}_thumb.jpg"
                _, thumbnail_url = await storage.save(
                    processed['thumbnail'],
                    thumb_filename,
                    "image/jpeg"
                )

            # Upload medium
            if processed['medium']:
                medium_filename = f"{base_name}_medium.jpg"
                _, medium_url = await storage.save(
                    processed['medium'],
                    medium_filename,
                    "image/jpeg"
                )

            # Upload large
            if processed['large']:
                large_filename = f"{base_name}_large.jpg"
                _, large_url = await storage.save(
                    processed['large'],
                    large_filename,
                    "image/jpeg"
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

                # Upload original video
                import io
                storage_path, original_url = await storage.save(
                    io.BytesIO(file_data),
                    unique_filename,
                    content_type
                )

                # Generate video thumbnail
                thumb_filename = f"{base_name}_thumb.jpg"
                temp_thumb_path = f"/tmp/{thumb_filename}"

                if VideoProcessor.generate_video_thumbnail(temp_video_path, temp_thumb_path):
                    with open(temp_thumb_path, 'rb') as thumb_file:
                        _, thumbnail_url = await storage.save(
                            thumb_file,
                            thumb_filename,
                            "image/jpeg"
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
            media=MediaOut.from_orm(media),
            message="Media uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading media: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading media: {str(e)}")


@router.get("/entity/{entity_type}/{entity_id}", response_model=MediaListOut)
def list_media_for_entity(
    entity_type: EntityType,
    entity_id: int,
    entity_field: Optional[EntityField] = None,
    db: Session = Depends(get_db)
):
    """
    List all media for a specific entity.
    Optionally filter by entity_field (e.g., only avatars or only gallery).
    """
    query = db.query(Media).filter(
        Media.entity_type == entity_type.value,
        Media.entity_id == entity_id
    )

    if entity_field:
        query = query.filter(Media.entity_field == entity_field.value)

    media_items = query.order_by(Media.sort_order, Media.created_at.desc()).all()

    return MediaListOut(
        items=[MediaOut.from_orm(m) for m in media_items],
        total=len(media_items)
    )


@router.get("/{media_id}", response_model=MediaOut)
def get_media(
    media_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific media item by ID"""
    media = db.query(Media).filter(Media.id == media_id).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    return MediaOut.from_orm(media)


@router.get("/public/{public_id}", response_model=MediaOut)
def get_media_by_public_id(
    public_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific media item by public ID"""
    media = db.query(Media).filter(Media.public_id == public_id).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    return MediaOut.from_orm(media)


@router.delete("/{media_id}", response_model=MediaDeleteResponse)
async def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a media item.
    Only the uploader or admin can delete.
    """
    media = db.query(Media).filter(Media.id == media_id).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Check permissions
    if media.uploaded_by != current_user['public_id'] and current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized to delete this media")

    try:
        # Delete from storage
        await storage.delete(media.storage_path)

        # Delete thumbnails/variants if they exist
        if media.thumbnail_url:
            thumb_path = media.storage_path.replace(Path(media.filename).name, f"{Path(media.filename).stem}_thumb.jpg")
            await storage.delete(thumb_path)

        # Delete from database
        db.delete(media)
        db.commit()

        logger.info(f"🗑️  Deleted media: id={media_id}, public_id={media.public_id}")

        return MediaDeleteResponse(
            message="Media deleted successfully",
            deleted_id=media_id
        )

    except Exception as e:
        logger.error(f"Error deleting media: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting media: {str(e)}")


# Serve uploaded files (for local development)
@router.get("/serve/{subdir}/{filename}")
async def serve_file(subdir: str, filename: str):
    """
    Serve uploaded files for local development.
    In production, use nginx or S3 to serve files.
    """
    file_path = Path("uploads") / subdir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
