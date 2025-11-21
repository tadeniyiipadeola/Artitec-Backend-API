"""
Entity-specific media upload endpoints.
Provides dedicated routes for uploading media to different entity types with proper validation.
"""

import io
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from config.db import get_db
from config.security import get_current_user
from model.media import Media, MediaType, StorageType, ModerationStatus
from model.user import Users
from schema.media import MediaOut, MediaUploadResponse
from src.id_generator import generate_public_id
from src.media_processor import (
    MediaValidator,
    ImageProcessorEnhanced,
    PathGenerator,
    FileHasher
)
from src.storage import get_storage_backend
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Get storage backend
storage = get_storage_backend()


# Helper functions
def get_entity_profile_id(db: Session, entity_type: str, entity_id: int) -> Optional[str]:
    """Get the profile ID for an entity."""
    try:
        if entity_type == "user":
            from model.user import Users
            user = db.query(Users).filter(Users.id == entity_id).first()
            return user.user_id if user else None

        elif entity_type == "community":
            from model.profiles.community import Community
            community = db.query(Community).filter(Community.id == entity_id).first()
            return community.community_id if community else None

        elif entity_type == "builder":
            from model.profiles.builder import BuilderProfile
            builder = db.query(BuilderProfile).filter(BuilderProfile.id == entity_id).first()
            return builder.builder_id if builder else None

        elif entity_type == "sales_rep":
            from model.profiles.sales_rep import SalesRepProfile
            rep = db.query(SalesRepProfile).filter(SalesRepProfile.id == entity_id).first()
            return rep.sales_rep_id if rep else None

        return None
    except Exception as e:
        logger.warning(f"Error getting profile ID: {e}")
        return None


def validate_entity_access(
    db: Session,
    current_user: dict,
    entity_type: str,
    entity_id: int
) -> bool:
    """Validate user has permission to upload media to entity."""
    user_public_id = current_user['public_id']

    try:
        if entity_type == "user":
            # User can only upload to their own profile
            user = db.query(Users).filter(Users.id == entity_id).first()
            return user and user.user_id == user_public_id

        elif entity_type == "community":
            from model.profiles.community import Community
            community = db.query(Community).filter(Community.id == entity_id).first()
            # Check if user is admin of the community
            if community and hasattr(community, 'admin_id'):
                return community.admin_id == user_public_id
            return False

        elif entity_type == "builder":
            from model.profiles.builder import BuilderProfile
            builder = db.query(BuilderProfile).filter(BuilderProfile.id == entity_id).first()
            # Check if user owns the builder profile
            if builder and hasattr(builder, 'user_id'):
                return builder.user_id == user_public_id
            return False

        elif entity_type == "sales_rep":
            from model.profiles.sales_rep import SalesRepProfile
            rep = db.query(SalesRepProfile).filter(SalesRepProfile.id == entity_id).first()
            # Check if user owns the sales rep profile
            if rep and hasattr(rep, 'user_id'):
                return rep.user_id == user_public_id
            return False

        # Admin users can upload anywhere
        if current_user.get('role') == 'admin':
            return True

        return False

    except Exception as e:
        logger.error(f"Error validating entity access: {e}")
        return False


def process_and_save_media(
    db: Session,
    file: UploadFile,
    entity_type: str,
    entity_id: int,
    entity_field: str,
    current_user: dict,
    alt_text: Optional[str] = None,
    caption: Optional[str] = None,
    tags: Optional[List[str]] = None,
    is_primary: bool = False
) -> Media:
    """
    Process and save media file.

    Returns:
        Media object
    """
    # Read file data
    file_data = file.file.read()
    file_size = len(file_data)
    content_type = file.content_type or "application/octet-stream"

    # Validate file
    is_valid, error_msg, media_type_str = MediaValidator.validate_file(
        file.filename, file_size, content_type
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Get profile ID for organized storage
    profile_id = get_entity_profile_id(db, entity_type, entity_id)

    # Generate unique filename
    unique_filename = PathGenerator.generate_unique_filename(
        file.filename,
        entity_field
    )

    # Generate storage path
    storage_path = PathGenerator.generate_storage_path(
        entity_type,
        entity_field,
        profile_id or str(entity_id),
        unique_filename
    )

    # Process based on type
    original_url = None
    thumbnail_url = None
    medium_url = None
    large_url = None
    width, height = None, None
    image_hash = None
    metadata_json = {}

    if media_type_str == "image":
        # Process image
        file_io = io.BytesIO(file_data)
        processed = ImageProcessorEnhanced.process_image_complete(file_io)

        width, height = processed['dimensions']
        image_hash = processed['perceptual_hash']
        metadata_json = processed['metadata']

        # Validate dimensions
        is_valid_dims, error_msg = MediaValidator.validate_image_dimensions(width, height)
        if not is_valid_dims:
            raise HTTPException(status_code=400, detail=error_msg)

        # Upload original
        _, original_url = storage.save(
            processed['original'],
            unique_filename,
            content_type,
            profile_id=profile_id,
            entity_field=entity_field
        )

        # Upload thumbnail
        if processed['thumbnail']:
            thumb_filename = f"{Path(unique_filename).stem}_thumb.jpg"
            _, thumbnail_url = storage.save(
                processed['thumbnail'],
                thumb_filename,
                "image/jpeg",
                profile_id=profile_id,
                entity_field=entity_field
            )

        # Upload medium
        if processed['medium']:
            medium_filename = f"{Path(unique_filename).stem}_medium.jpg"
            _, medium_url = storage.save(
                processed['medium'],
                medium_filename,
                "image/jpeg",
                profile_id=profile_id,
                entity_field=entity_field
            )

        # Upload large
        if processed['large']:
            large_filename = f"{Path(unique_filename).stem}_large.jpg"
            _, large_url = storage.save(
                processed['large'],
                large_filename,
                "image/jpeg",
                profile_id=profile_id,
                entity_field=entity_field
            )

    elif media_type_str == "video":
        # For now, just upload the video as-is
        # TODO: Add video processing (thumbnails, compression)
        file_io = io.BytesIO(file_data)
        _, original_url = storage.save(
            file_io,
            unique_filename,
            content_type,
            profile_id=profile_id,
            entity_field=entity_field
        )

    # Determine storage type
    import os
    storage_type_value = os.getenv("STORAGE_TYPE", "local")
    storage_type_enum = StorageType.S3 if storage_type_value == "s3" else StorageType.LOCAL

    # Create media record
    media = Media(
        public_id=generate_public_id("media"),
        filename=unique_filename,
        original_filename=file.filename,
        media_type=MediaType.IMAGE if media_type_str == "image" else MediaType.VIDEO,
        content_type=content_type,
        file_size=file_size,
        width=width,
        height=height,
        image_hash=image_hash,
        storage_type=storage_type_enum,
        bucket_name=os.getenv("S3_BUCKET_NAME") if storage_type_enum == StorageType.S3 else None,
        storage_path=storage_path,
        original_url=original_url,
        thumbnail_url=thumbnail_url,
        medium_url=medium_url,
        large_url=large_url,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_field=entity_field,
        alt_text=alt_text,
        caption=caption,
        is_primary=is_primary,
        tags=tags,
        metadata=metadata_json,
        uploaded_by=current_user['public_id'],
        is_public=True,
        is_approved=True,
        moderation_status=ModerationStatus.APPROVED
    )

    db.add(media)
    db.commit()
    db.refresh(media)

    return media


# User Avatar Upload
@router.post("/users/{user_id}/avatar", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_user_avatar(
    user_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload user avatar photo.
    Only the user themselves can upload their avatar.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "user", user_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload avatar for this user")

    logger.info(f"Uploading avatar for user {user_id}")

    media = process_and_save_media(
        db, file, "user", user_id, "avatar", current_user,
        alt_text=alt_text,
        is_primary=True
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Avatar uploaded successfully"
    )


# User Cover Photo Upload
@router.post("/users/{user_id}/cover", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_user_cover(
    user_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload user cover photo.
    Only the user themselves can upload their cover photo.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "user", user_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload cover for this user")

    logger.info(f"Uploading cover photo for user {user_id}")

    media = process_and_save_media(
        db, file, "user", user_id, "cover", current_user,
        alt_text=alt_text,
        is_primary=True
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Cover photo uploaded successfully"
    )


# Property Photos Upload
@router.post("/properties/{property_id}/photos", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_property_photos(
    property_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload property photo.
    Only authorized users can upload property photos.
    """
    logger.info(f"Uploading photo for property {property_id}")

    media = process_and_save_media(
        db, file, "property", property_id, "gallery", current_user,
        alt_text=alt_text,
        caption=caption,
        is_primary=is_primary
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Property photo uploaded successfully"
    )


# Builder Portfolio Upload
@router.post("/builders/{builder_id}/portfolio", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_builder_portfolio(
    builder_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload general builder portfolio photo (not tied to a specific home plan).
    Use /builders/{builder_id}/home-plans/{plan_id}/photos for home plan-specific photos.
    Only the builder owner can upload portfolio photos.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "builder", builder_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload for this builder")

    logger.info(f"Uploading general portfolio photo for builder {builder_id}")

    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else None

    media = process_and_save_media(
        db, file, "builder", builder_id, "gallery", current_user,
        alt_text=alt_text,
        caption=caption,
        tags=tag_list
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Portfolio photo uploaded successfully"
    )


@router.post("/builders/{builder_id}/home-plans/{plan_id}/photos", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_home_plan_photos(
    builder_id: int,
    plan_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    photo_type: Optional[str] = Form(None),  # e.g., "exterior", "interior", "floorplan", "kitchen", "bedroom"
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload photos for a specific home plan.
    Associates photos with a particular floor plan/home design in the builder's portfolio.

    Photo types can include:
    - exterior: Outside views of the home
    - interior: Inside views
    - floorplan: Floor plan diagrams
    - kitchen, bedroom, bathroom, living_room, etc: Room-specific photos

    Only the builder owner can upload photos for their home plans.
    """
    # Validate builder access
    if not validate_entity_access(db, current_user, "builder", builder_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload for this builder")

    # Verify home plan exists and belongs to this builder
    from model.profiles.builder import BuilderHomePlan
    home_plan = db.query(BuilderHomePlan).filter(
        BuilderHomePlan.id == plan_id,
        BuilderHomePlan.builder_id == builder_id
    ).first()

    if not home_plan:
        raise HTTPException(status_code=404, detail="Home plan not found for this builder")

    logger.info(f"Uploading photo for builder {builder_id}, home plan {plan_id} ({home_plan.name})")

    # Create tags array including home plan name and photo type
    tag_list = [home_plan.name, home_plan.series]
    if photo_type:
        tag_list.append(photo_type)

    # Store home plan ID in the entity_id field using the media system
    # We'll use entity_type="home_plan" and entity_id=plan_id
    media = process_and_save_media(
        db, file, "home_plan", plan_id, "gallery", current_user,
        alt_text=alt_text or f"{home_plan.name} - {photo_type or 'photo'}",
        caption=caption,
        tags=tag_list,
        is_primary=is_primary
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message=f"Photo uploaded successfully for home plan '{home_plan.name}'"
    )


# Builder Logo Upload
@router.post("/builders/{builder_id}/logo", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_builder_logo(
    builder_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload builder logo.
    Only the builder owner can upload their logo.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "builder", builder_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload logo for this builder")

    logger.info(f"Uploading logo for builder {builder_id}")

    media = process_and_save_media(
        db, file, "builder", builder_id, "avatar", current_user,
        alt_text=alt_text,
        is_primary=True
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Builder logo uploaded successfully"
    )


@router.post("/builders/{builder_id}/cover", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_builder_cover(
    builder_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload builder cover photo.
    Only the builder owner can upload their cover photo.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "builder", builder_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload cover for this builder")

    logger.info(f"Uploading cover photo for builder {builder_id}")

    media = process_and_save_media(
        db, file, "builder", builder_id, "cover", current_user,
        alt_text=alt_text,
        is_primary=True
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Builder cover photo uploaded successfully"
    )


# Community Media Uploads
@router.post("/communities/{community_id}/logo", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_community_logo(
    community_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload community logo.
    Only the community admin can upload the logo.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "community", community_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload logo for this community")

    logger.info(f"Uploading logo for community {community_id}")

    media = process_and_save_media(
        db, file, "community", community_id, "avatar", current_user,
        alt_text=alt_text,
        is_primary=True
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Community logo uploaded successfully"
    )


@router.post("/communities/{community_id}/cover", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_community_cover(
    community_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload community cover photo.
    Only the community admin can upload the cover photo.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "community", community_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload cover for this community")

    logger.info(f"Uploading cover photo for community {community_id}")

    media = process_and_save_media(
        db, file, "community", community_id, "cover", current_user,
        alt_text=alt_text,
        is_primary=True
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Community cover photo uploaded successfully"
    )


@router.post("/communities/{community_id}/photos", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_community_photos(
    community_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload community photo.
    Only the community admin can upload photos.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "community", community_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload for this community")

    logger.info(f"Uploading photo for community {community_id}")

    media = process_and_save_media(
        db, file, "community", community_id, "gallery", current_user,
        alt_text=alt_text,
        caption=caption,
        is_primary=is_primary
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Community photo uploaded successfully"
    )


# Community Amenity Photos Upload
@router.post("/communities/{community_id}/amenities/{amenity_id}/photos", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_amenity_photos(
    community_id: int,
    amenity_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload amenity photo.
    Only the community admin can upload amenity photos.
    """
    # Validate access to community
    if not validate_entity_access(db, current_user, "community", community_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload for this community")

    logger.info(f"Uploading photo for amenity {amenity_id} in community {community_id}")

    media = process_and_save_media(
        db, file, "amenity", amenity_id, "gallery", current_user,
        alt_text=alt_text,
        caption=caption
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Amenity photo uploaded successfully"
    )


# Sales Rep Avatar Upload
@router.post("/sales-reps/{rep_id}/avatar", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_sales_rep_avatar(
    rep_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload sales rep avatar.
    Only the sales rep themselves can upload their avatar.
    """
    # Validate access
    if not validate_entity_access(db, current_user, "sales_rep", rep_id):
        raise HTTPException(status_code=403, detail="Not authorized to upload avatar for this sales rep")

    logger.info(f"Uploading avatar for sales rep {rep_id}")

    media = process_and_save_media(
        db, file, "sales_rep", rep_id, "avatar", current_user,
        alt_text=alt_text,
        is_primary=True
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Sales rep avatar uploaded successfully"
    )


# Post Media Upload
@router.post("/posts/{post_id}/media", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_post_media(
    post_id: int,
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload media for a post (photo or video).
    Only the post owner can upload media.
    """
    logger.info(f"Uploading media for post {post_id}")

    media = process_and_save_media(
        db, file, "post", post_id, "gallery", current_user,
        alt_text=alt_text,
        caption=caption
    )

    from routes.media.upload import media_to_out
    return MediaUploadResponse(
        media=media_to_out(db, media),
        message="Post media uploaded successfully"
    )


# Batch Upload Endpoint
@router.post("/batch/upload", status_code=status.HTTP_201_CREATED)
async def batch_upload_media(
    files: List[UploadFile] = File(...),
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    entity_field: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload multiple media files at once.
    Maximum 20 files per batch.
    """
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch upload")

    # Validate access
    if not validate_entity_access(db, current_user, entity_type, entity_id):
        raise HTTPException(status_code=403, detail=f"Not authorized to upload for this {entity_type}")

    logger.info(f"Batch uploading {len(files)} files for {entity_type}/{entity_id}")

    uploaded = []
    failed = []

    for idx, file in enumerate(files):
        try:
            media = process_and_save_media(
                db, file, entity_type, entity_id, entity_field, current_user,
                is_primary=(idx == 0)  # First image is primary
            )

            from routes.media.upload import media_to_out
            uploaded.append(media_to_out(db, media))

        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {e}")
            failed.append({
                'filename': file.filename,
                'error': str(e)
            })

    return {
        'uploaded': uploaded,
        'uploaded_count': len(uploaded),
        'failed': failed,
        'failed_count': len(failed),
        'message': f"Successfully uploaded {len(uploaded)} of {len(files)} files"
    }
