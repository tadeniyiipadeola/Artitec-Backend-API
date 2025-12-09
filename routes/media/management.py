"""
Media management endpoints - CRUD operations, batch operations, analytics
"""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config.db import get_db
from model.media import Media, MediaType
from schema.media import (
    MediaOut, MediaListOut, MediaDeleteResponse, MediaUpdateRequest,
    EntityType, EntityField
)
from config.security import get_current_user
from src.storage import get_storage_backend
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


# Helper to validate media file exists in storage
def validate_media_exists(media: Media) -> bool:
    """
    Check if the media file actually exists in storage.
    Returns False if the file is missing (orphaned database record).
    """
    try:
        # Skip validation for embedded videos (Vimeo, YouTube)
        if media.media_type == MediaType.VIDEO and media.content_type == "video/embed":
            return True

        # Check if the primary file exists
        if not media.storage_path:
            logger.warning(f"Media {media.id} has no storage_path")
            return False

        # Check file existence in storage
        exists = storage.file_exists(media.storage_path)

        if not exists:
            logger.warning(f"❌ Orphaned record detected: Media ID {media.id} - file not found: {media.storage_path}")

        return exists

    except Exception as e:
        logger.error(f"Error validating media {media.id}: {e}")
        # Return True on error to avoid hiding media due to temporary issues
        return True


# Helper to convert Media to MediaOut with profile ID
def media_to_out(db: Session, media: Media, preferred_size: str = "medium") -> MediaOut:
    """
    Convert Media ORM object to MediaOut schema with entity_profile_id populated.

    Args:
        db: Database session
        media: Media ORM object
        preferred_size: Preferred image size ('thumbnail', 'medium', 'large', 'original')
    """
    # Get base URL from environment for converting old relative URLs
    base_url = os.getenv("BASE_URL", "http://localhost:8000")

    # Build full URLs
    original_url = make_full_url(media.original_url, base_url)
    thumbnail_url = make_full_url(media.thumbnail_url, base_url)
    medium_url = make_full_url(media.medium_url, base_url)
    large_url = make_full_url(media.large_url, base_url)

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
        "original_url": original_url,
        "thumbnail_url": thumbnail_url,
        "medium_url": medium_url,
        "large_url": large_url,
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


# Access control helper
def check_media_access(media: Media, current_user, db: Session) -> bool:
    """
    Check if user can access/modify this media.

    Returns:
        True if user has access, False otherwise
    """
    # Owner can always access
    if media.uploaded_by == current_user.user_id:
        return True

    # Check if user is admin of the entity
    if media.entity_type == "community":
        from model.profiles.community import Community
        community = db.query(Community).filter(Community.id == media.entity_id).first()
        if community and hasattr(community, 'admin_id'):
            return community.admin_id == current_user.user_id

    elif media.entity_type == "builder":
        from model.profiles.builder import BuilderProfile
        builder = db.query(BuilderProfile).filter(BuilderProfile.id == media.entity_id).first()
        if builder and hasattr(builder, 'user_id'):
            return builder.user_id == current_user.user_id

    # Admin users can access everything (if you have a role system)
    if hasattr(current_user, 'role') and current_user.role == 'admin':
        return True

    return False


@router.get("/entity/{entity_type}/{entity_id}", response_model=MediaListOut, response_model_by_alias=True)
def list_media_for_entity(
    entity_type: EntityType,
    entity_id: int,
    entity_field: Optional[EntityField] = None,
    db: Session = Depends(get_db)
):
    """
    List all media for a specific entity.
    Optionally filter by entity_field (e.g., only avatars or only gallery).
    Validates that files exist in storage before returning.
    """
    query = db.query(Media).filter(
        Media.entity_type == entity_type.value,
        Media.entity_id == entity_id
    )

    if entity_field:
        query = query.filter(Media.entity_field == entity_field.value)

    media_items = query.order_by(Media.sort_order, Media.created_at.desc()).all()

    # Filter out orphaned records (files that don't exist in storage)
    validated_media = [m for m in media_items if validate_media_exists(m)]

    # Log if any orphans were found
    orphan_count = len(media_items) - len(validated_media)
    if orphan_count > 0:
        logger.warning(f"⚠️ Found {orphan_count} orphaned media records for {entity_type.value}/{entity_id}")

    return MediaListOut(
        items=[media_to_out(db, m) for m in validated_media],
        total=len(validated_media)
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

    return media_to_out(db, media)


@router.get("/public/{public_id}", response_model=MediaOut)
def get_media_by_public_id(
    public_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific media item by public ID"""
    media = db.query(Media).filter(Media.public_id == public_id).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    return media_to_out(db, media)


@router.patch("/{media_id}", response_model=MediaOut, response_model_by_alias=True)
async def update_media(
    media_id: int,
    update_data: MediaUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update media metadata including entity_field (e.g., set as avatar or cover photo).

    When setting entity_field to 'avatar' or 'cover':
    - Any existing media with that entity_field will be moved back to 'gallery'
    - The selected media will be set to the new entity_field
    """
    media = db.query(Media).filter(Media.id == media_id).first()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Check permissions
    if not check_media_access(media, current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized to update this media")

    # Handle entity_field change (e.g., setting as avatar or cover)
    if update_data.entity_field is not None:
        new_field = update_data.entity_field.value if hasattr(update_data.entity_field, 'value') else update_data.entity_field

        # If setting to avatar or cover, clear any existing media with that field
        if new_field in ['avatar', 'cover']:
            existing_media = db.query(Media).filter(
                Media.entity_type == media.entity_type,
                Media.entity_id == media.entity_id,
                Media.entity_field == new_field,
                Media.id != media_id
            ).all()

            # Move existing avatar/cover back to gallery
            for existing in existing_media:
                existing.entity_field = 'gallery'
                logger.info(f"Moved media {existing.id} from {new_field} to gallery")

        media.entity_field = new_field
        logger.info(f"Updated media {media_id} entity_field to '{new_field}'")

    # Update other fields
    if update_data.alt_text is not None:
        media.alt_text = update_data.alt_text
    if update_data.caption is not None:
        media.caption = update_data.caption
    if update_data.sort_order is not None:
        media.sort_order = update_data.sort_order
    if update_data.is_public is not None:
        media.is_public = update_data.is_public
    if update_data.is_primary is not None:
        media.is_primary = update_data.is_primary
    if update_data.tags is not None:
        media.tags = update_data.tags
    if update_data.moderation_status is not None:
        media.moderation_status = update_data.moderation_status

    db.commit()
    db.refresh(media)

    return media_to_out(db, media)


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
    if media.uploaded_by != current_user.user_id and getattr(current_user, 'role', None) != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized to delete this media")

    try:
        # Cascading delete - remove ALL files from storage first
        files_to_delete = []

        # Original file
        if media.storage_path:
            files_to_delete.append(media.storage_path)

        # All variants - extract storage paths from URLs
        if media.thumbnail_url and not media.thumbnail_url.startswith(('http://', 'https://')):
            files_to_delete.append(media.thumbnail_url)
        elif media.thumbnail_url:
            # Extract path from full URL (e.g., http://domain/bucket/path -> path)
            thumb_path = media.thumbnail_url.split('/')[-1]
            if thumb_path:
                files_to_delete.append(thumb_path)

        if media.medium_url and not media.medium_url.startswith(('http://', 'https://')):
            files_to_delete.append(media.medium_url)
        elif media.medium_url:
            medium_path = media.medium_url.split('/')[-1]
            if medium_path:
                files_to_delete.append(medium_path)

        if media.large_url and not media.large_url.startswith(('http://', 'https://')):
            files_to_delete.append(media.large_url)
        elif media.large_url:
            large_path = media.large_url.split('/')[-1]
            if large_path:
                files_to_delete.append(large_path)

        # Video processed URL
        if media.video_processed_url and not media.video_processed_url.startswith(('http://', 'https://')):
            files_to_delete.append(media.video_processed_url)

        # Delete all files from storage
        deleted_files = []
        for file_path in files_to_delete:
            try:
                success = await storage.delete(file_path)
                if success:
                    deleted_files.append(file_path)
                    logger.info(f"🗑️ Deleted file: {file_path}")
            except Exception as del_error:
                logger.warning(f"⚠️  Failed to delete {file_path}: {del_error}")

        # Delete from database (even if some files failed to delete)
        db.delete(media)
        db.commit()

        logger.info(f"🗑️  Deleted media: id={media_id}, public_id={media.public_id}, files={len(deleted_files)}/{len(files_to_delete)}")

        return MediaDeleteResponse(
            message=f"Media deleted successfully ({len(deleted_files)} files removed)",
            deleted_id=media_id
        )

    except Exception as e:
        logger.error(f"Error deleting media: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting media: {str(e)}")


@router.post("/batch/delete")
async def batch_delete_media(
    media_ids: List[int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete multiple media items at once.
    Only the uploader or entity admin can delete.
    """
    if not media_ids:
        raise HTTPException(status_code=400, detail="No media IDs provided")

    if len(media_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per batch")

    deleted = []
    failed = []

    for media_id in media_ids:
        try:
            media = db.query(Media).filter(Media.id == media_id).first()

            if not media:
                failed.append({"id": media_id, "error": "Media not found"})
                continue

            # Check permissions
            if not check_media_access(media, current_user, db):
                failed.append({"id": media_id, "error": "Not authorized"})
                continue

            # Delete from storage
            try:
                await storage.delete(media.storage_path)

                # Delete thumbnails/variants
                if media.thumbnail_url:
                    thumb_path = media.storage_path.replace(
                        Path(media.filename).name,
                        f"{Path(media.filename).stem}_thumb.jpg"
                    )
                    await storage.delete(thumb_path)

                if media.medium_url:
                    medium_path = media.storage_path.replace(
                        Path(media.filename).name,
                        f"{Path(media.filename).stem}_medium.jpg"
                    )
                    await storage.delete(medium_path)

                if media.large_url:
                    large_path = media.storage_path.replace(
                        Path(media.filename).name,
                        f"{Path(media.filename).stem}_large.jpg"
                    )
                    await storage.delete(large_path)
            except Exception as storage_error:
                logger.warning(f"Storage deletion warning for {media_id}: {storage_error}")

            # Delete from database
            db.delete(media)
            deleted.append(media_id)

            logger.info(f"🗑️  Batch deleted media: id={media_id}, public_id={media.public_id}")

        except Exception as e:
            logger.error(f"Error deleting media {media_id}: {e}")
            failed.append({"id": media_id, "error": str(e)})

    # Commit all deletions
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error committing deletions: {str(e)}")

    return {
        "deleted": deleted,
        "deleted_count": len(deleted),
        "failed": failed,
        "failed_count": len(failed),
        "message": f"Successfully deleted {len(deleted)} items"
    }


@router.post("/batch/approve")
async def approve_media_batch(
    media_ids: List[int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Approve (keep) multiple media items to prevent auto-deletion.

    Scraped media starts as unapproved and is auto-deleted after 7 days.
    Use this endpoint to mark selected media as approved/permanent.
    """
    if len(media_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per batch")

    approved = []
    failed = []
    communities_to_update = set()  # Track unique community IDs

    for media_id in media_ids:
        media = db.query(Media).filter(Media.id == media_id).first()

        if not media:
            failed.append({"id": media_id, "error": "Media not found"})
            continue

        # Check access permission
        if not check_media_access(media, current_user, db):
            failed.append({"id": media_id, "error": "Not authorized"})
            continue

        # Approve media
        media.is_approved = True
        approved.append(media_id)

        # Track community for data_source update
        if media.entity_type == "community":
            communities_to_update.add(media.entity_id)

    # Update data_source for affected communities and apply pending changes
    if communities_to_update:
        from model.profiles.community import Community
        from model.collection import CollectionChange
        from datetime import datetime
        import json

        for community_id in communities_to_update:
            community = db.query(Community).filter(Community.id == community_id).first()
            if not community:
                continue

            # Apply any pending collection changes for this community
            pending_changes = db.query(CollectionChange).filter(
                CollectionChange.entity_type == 'community',
                CollectionChange.entity_id == community_id,
                CollectionChange.status == 'pending'
            ).all()

            applied_fields = []
            for change in pending_changes:
                if change.field_name and hasattr(community, change.field_name):
                    # Parse new_value if it's JSON
                    try:
                        new_value = json.loads(change.new_value) if change.new_value else None
                    except (json.JSONDecodeError, TypeError):
                        new_value = change.new_value

                    # Apply the change
                    setattr(community, change.field_name, new_value)
                    applied_fields.append(change.field_name)

                    # Mark change as applied
                    change.status = 'applied'
                    change.reviewed_by = current_user.user_id
                    change.reviewed_at = datetime.utcnow()

            # Update data_source to indicate manual collection/curation
            community.data_source = 'collected_manual'
            community.last_data_sync = datetime.utcnow()

            if applied_fields:
                logger.info(f"✅ Applied {len(applied_fields)} pending changes to community {community_id}: {applied_fields}")

    db.commit()

    logger.info(f"✅ Approved {len(approved)} media items for user {current_user.user_id}")
    if communities_to_update:
        logger.info(f"✅ Updated data_source='collected_manual' for {len(communities_to_update)} communities: {communities_to_update}")

    return {
        "approved": approved,
        "approved_count": len(approved),
        "failed": failed,
        "failed_count": len(failed),
        "message": f"Successfully approved {len(approved)} items"
    }


@router.get("/analytics/storage")
async def get_storage_analytics(
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get storage usage statistics"""
    from sqlalchemy import func

    query = db.query(
        Media.entity_type,
        Media.media_type,
        func.count(Media.id).label('count'),
        func.sum(Media.file_size).label('total_size')
    )

    if entity_type:
        query = query.filter(Media.entity_type == entity_type)

    stats = query.group_by(Media.entity_type, Media.media_type).all()

    total_files = sum(stat.count for stat in stats)
    total_size = sum(stat.total_size or 0 for stat in stats)

    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2) if total_size else 0,
        "total_size_gb": round(total_size / 1024 / 1024 / 1024, 2) if total_size else 0,
        "by_entity_and_type": [
            {
                "entity_type": stat.entity_type,
                "media_type": stat.media_type.value,
                "count": stat.count,
                "total_size_mb": round((stat.total_size or 0) / 1024 / 1024, 2)
            }
            for stat in stats
        ]
    }


@router.get("/health/storage-sync")
async def check_storage_sync(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Health check endpoint to verify database and storage are in sync.
    Returns counts of orphaned records and missing files.
    """
    total_records = db.query(Media).count()
    orphaned_count = 0
    validated_count = 0

    # Sample check (first 100 records) to avoid performance issues
    sample_size = min(100, total_records)
    media_sample = db.query(Media).limit(sample_size).all()

    for media in media_sample:
        # Skip embedded videos
        if media.media_type == MediaType.VIDEO and media.content_type == "video/embed":
            validated_count += 1
            continue

        # Check if file exists
        if media.storage_path and storage.file_exists(media.storage_path):
            validated_count += 1
        else:
            orphaned_count += 1
            logger.warning(f"Orphan found in health check: {media.id} - {media.storage_path}")

    # Calculate estimated totals based on sample
    if sample_size > 0:
        orphan_ratio = orphaned_count / sample_size
        estimated_orphans = int(total_records * orphan_ratio)
    else:
        estimated_orphans = 0

    health_status = "healthy" if orphaned_count == 0 else "degraded" if orphaned_count < 10 else "critical"

    return {
        "status": health_status,
        "total_records": total_records,
        "sample_size": sample_size,
        "validated": validated_count,
        "orphaned_in_sample": orphaned_count,
        "estimated_total_orphans": estimated_orphans,
        "storage_type": os.getenv("STORAGE_TYPE", "local").upper(),
        "timestamp": str(datetime.now())
    }


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
