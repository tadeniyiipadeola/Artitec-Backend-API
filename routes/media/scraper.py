"""
Media Scraper API Endpoints

Endpoints for scraping media from external websites.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field

from config.db import get_db
from src.media_scraper import MediaScraper
from schema.media import MediaOut
from model.user import Users
from config.security import get_current_user
from routes.media.upload import media_to_out

router = APIRouter(prefix="/scraper")


# Request/Response Schemas

class ScrapePageRequest(BaseModel):
    """Request to scrape media from a webpage"""
    url: HttpUrl
    entity_type: str = Field(..., description="Entity type (community, property, etc.)")
    entity_id: int = Field(..., description="Entity ID")
    entity_field: Optional[str] = Field(None, description="Optional field (gallery, cover, etc.)")
    max_images: Optional[int] = Field(None, description="Maximum images to scrape", ge=1, le=100)
    max_videos: Optional[int] = Field(None, description="Maximum videos to scrape", ge=1, le=20)

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/the-highland",
                "entity_type": "community",
                "entity_id": 1,
                "entity_field": "gallery",
                "max_images": 20,
                "max_videos": 5
            }
        }


class DownloadFromUrlRequest(BaseModel):
    """Request to download media from direct URL"""
    media_url: HttpUrl
    entity_type: str
    entity_id: int
    entity_field: Optional[str] = None
    caption: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "media_url": "https://example.com/images/photo.jpg",
                "entity_type": "community",
                "entity_id": 1,
                "entity_field": "gallery",
                "caption": "Beautiful view"
            }
        }


class ScrapeResponse(BaseModel):
    """Response from scraping operation"""
    success: bool
    media_count: int
    media: List[MediaOut]
    errors: List[str]
    message: str

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "success": True,
                "mediaCount": 5,
                "media": [],
                "errors": [],
                "message": "Successfully scraped 5 media items"
            }
        }

    def model_dump(self, **kwargs):
        """Override to use camelCase for JSON serialization"""
        data = super().model_dump(**kwargs)
        return {
            "success": data["success"],
            "mediaCount": data["media_count"],
            "media": data["media"],
            "errors": data["errors"],
            "message": data["message"]
        }


class BatchDownloadRequest(BaseModel):
    """Request to download multiple media URLs"""
    media_urls: List[HttpUrl] = Field(..., min_length=1, max_length=50)
    entity_type: str
    entity_id: int
    entity_field: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "media_urls": [
                    "https://example.com/photo1.jpg",
                    "https://example.com/photo2.jpg",
                    "https://example.com/video1.mp4"
                ],
                "entity_type": "community",
                "entity_id": 1,
                "entity_field": "gallery"
            }
        }


# Endpoints

@router.post("/scrape-page", response_model=ScrapeResponse)
async def scrape_webpage(
    request: ScrapePageRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """
    Scrape images and videos from a webpage URL

    This endpoint will:
    1. Fetch the HTML from the provided URL
    2. Extract all image and video URLs
    3. Download and upload them to your media storage
    4. Associate them with the specified entity

    Example: Scrape The Highland's builder website to import all photos and videos.
    """
    try:
        # Initialize scraper
        scraper = MediaScraper(db=db, uploaded_by=current_user.user_id)

        # Scrape the page
        media_objects, errors = await scraper.scrape_page(
            url=str(request.url),
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_field=request.entity_field,
            max_images=request.max_images,
            max_videos=request.max_videos
        )

        # Convert to response schema with entity profile IDs
        media_list = [media_to_out(db, media) for media in media_objects]

        return ScrapeResponse(
            success=len(media_objects) > 0,
            media_count=len(media_objects),
            media=media_list,
            errors=errors,
            message=f"Successfully scraped {len(media_objects)} media items" if media_objects else "No media found or all failed"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape page: {str(e)}"
        )


@router.post("/download-url", response_model=MediaOut)
async def download_from_url(
    request: DownloadFromUrlRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """
    Download a single image or video from a direct URL

    Provide a direct URL to an image or video file, and it will be downloaded
    and uploaded to your media storage.

    Example: Download a specific photo from The Highland's website.
    """
    try:
        # Initialize scraper
        scraper = MediaScraper(db=db, uploaded_by=current_user.user_id)

        # Download and upload
        media = await scraper.download_from_url(
            media_url=str(request.media_url),
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_field=request.entity_field,
            caption=request.caption
        )

        if not media:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to download media or unsupported format"
            )

        return media_to_out(db, media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download media: {str(e)}"
        )


@router.post("/batch-download", response_model=ScrapeResponse)
async def batch_download_urls(
    request: BatchDownloadRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """
    Download multiple media files from direct URLs

    Provide a list of direct URLs to images/videos, and they will all be
    downloaded and uploaded to your media storage.

    Example: Import a list of specific photos/videos from The Highland.
    """
    try:
        # Initialize scraper
        scraper = MediaScraper(db=db, uploaded_by=current_user.user_id)

        media_objects = []
        errors = []

        # Download each URL
        for media_url in request.media_urls:
            try:
                media = await scraper.download_from_url(
                    media_url=str(media_url),
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    entity_field=request.entity_field
                )
                if media:
                    media_objects.append(media)
            except Exception as e:
                errors.append(f"Failed to download {media_url}: {str(e)}")

        # Convert to response schema with entity profile IDs
        media_list = [media_to_out(db, media) for media in media_objects]

        return ScrapeResponse(
            success=len(media_objects) > 0,
            media_count=len(media_objects),
            media=media_list,
            errors=errors,
            message=f"Successfully downloaded {len(media_objects)} of {len(request.media_urls)} media items"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch download media: {str(e)}"
        )


@router.get("/health")
async def scraper_health():
    """Check if scraper service is available"""
    return {
        "status": "healthy",
        "service": "media_scraper",
        "message": "Media scraper is ready to process requests"
    }
