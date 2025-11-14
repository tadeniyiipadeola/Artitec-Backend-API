"""
Media Scraper Service

Scrapes images and videos from websites and uploads them to the media system.
"""

import io
import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from model.media import Media, MediaType
from src.media_processing import ImageProcessor, VideoProcessor
from src.storage import get_storage_backend

logger = logging.getLogger(__name__)


class MediaScraper:
    """Scrapes media from websites and uploads to storage"""

    # Common image extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}

    # Common video extensions
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.m4v'}

    # User agent to avoid blocking
    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

    def __init__(self, db: Session, uploaded_by: str):
        """
        Initialize scraper

        Args:
            db: Database session
            uploaded_by: User ID uploading the media
        """
        self.db = db
        self.uploaded_by = uploaded_by
        self.storage = get_storage_backend()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.USER_AGENT})

    async def scrape_page(
        self,
        url: str,
        entity_type: str,
        entity_id: int,
        entity_field: Optional[str] = None,
        max_images: Optional[int] = None,
        max_videos: Optional[int] = None
    ) -> Tuple[List[Media], List[str]]:
        """
        Scrape images and videos from a webpage

        Args:
            url: URL of the webpage to scrape
            entity_type: Type of entity to attach media to
            entity_id: ID of the entity
            entity_field: Optional field to categorize media
            max_images: Maximum number of images to scrape
            max_videos: Maximum number of videos to scrape

        Returns:
            Tuple of (list of created Media objects, list of error messages)
        """
        logger.info(f"🕷️ Scraping media from: {url}")

        try:
            # Fetch the webpage
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract media URLs
            image_urls = self._extract_image_urls(soup, url)
            video_urls = self._extract_video_urls(soup, url)

            logger.info(f"📸 Found {len(image_urls)} images and 🎬 {len(video_urls)} videos")

            # Limit if specified
            if max_images:
                image_urls = image_urls[:max_images]
            if max_videos:
                video_urls = video_urls[:max_videos]

            # Download and upload media
            media_objects = []
            errors = []

            # Process images
            for img_url in image_urls:
                try:
                    media = await self._download_and_upload_image(
                        img_url, entity_type, entity_id, entity_field
                    )
                    if media:
                        media_objects.append(media)
                        logger.info(f"✅ Uploaded image: {media.public_id}")
                except Exception as e:
                    error_msg = f"Failed to upload {img_url}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)

            # Process videos
            for vid_url in video_urls:
                try:
                    media = await self._download_and_upload_video(
                        vid_url, entity_type, entity_id, entity_field
                    )
                    if media:
                        media_objects.append(media)
                        logger.info(f"✅ Uploaded video: {media.public_id}")
                except Exception as e:
                    error_msg = f"Failed to upload {vid_url}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)

            return media_objects, errors

        except Exception as e:
            logger.error(f"❌ Failed to scrape {url}: {e}")
            return [], [f"Failed to scrape page: {str(e)}"]

    async def download_from_url(
        self,
        media_url: str,
        entity_type: str,
        entity_id: int,
        entity_field: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Optional[Media]:
        """
        Download a single image or video from a direct URL

        Args:
            media_url: Direct URL to image or video
            entity_type: Type of entity to attach media to
            entity_id: ID of the entity
            entity_field: Optional field to categorize media
            caption: Optional caption

        Returns:
            Created Media object or None if failed
        """
        logger.info(f"📥 Downloading media from: {media_url}")

        # Determine if image or video
        ext = self._get_file_extension(media_url)

        if ext in self.IMAGE_EXTENSIONS:
            return await self._download_and_upload_image(
                media_url, entity_type, entity_id, entity_field, caption
            )
        elif ext in self.VIDEO_EXTENSIONS:
            return await self._download_and_upload_video(
                media_url, entity_type, entity_id, entity_field, caption
            )
        else:
            logger.warning(f"⚠️ Unknown media type for: {media_url}")
            return None

    def _extract_image_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all image URLs from HTML"""
        image_urls = []

        # Find all <img> tags
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, src)

                # Filter out small images (likely icons/logos)
                if self._is_valid_image_url(absolute_url):
                    image_urls.append(absolute_url)

        # Find images in <picture> tags
        for picture in soup.find_all('picture'):
            for source in picture.find_all('source'):
                srcset = source.get('srcset')
                if srcset:
                    # Parse srcset (format: "url 1x, url 2x")
                    urls = re.findall(r'(https?://[^\s,]+)', srcset)
                    for url in urls:
                        if self._is_valid_image_url(url):
                            image_urls.append(url)

        # Find background images in CSS
        for element in soup.find_all(style=True):
            style = element.get('style', '')
            bg_urls = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', style)
            for bg_url in bg_urls:
                absolute_url = urljoin(base_url, bg_url)
                if self._is_valid_image_url(absolute_url):
                    image_urls.append(absolute_url)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(image_urls))

    def _extract_video_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all video URLs from HTML"""
        video_urls = []

        # Find all <video> tags
        for video in soup.find_all('video'):
            src = video.get('src')
            if src:
                absolute_url = urljoin(base_url, src)
                if self._is_valid_video_url(absolute_url):
                    video_urls.append(absolute_url)

            # Check <source> tags within <video>
            for source in video.find_all('source'):
                src = source.get('src')
                if src:
                    absolute_url = urljoin(base_url, src)
                    if self._is_valid_video_url(absolute_url):
                        video_urls.append(absolute_url)

        # Find iframe embeds (YouTube, Vimeo, etc.)
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            # YouTube
            if 'youtube.com' in src or 'youtu.be' in src:
                video_urls.append(src)
            # Vimeo
            elif 'vimeo.com' in src:
                video_urls.append(src)

        # Remove duplicates
        return list(dict.fromkeys(video_urls))

    async def _download_and_upload_image(
        self,
        url: str,
        entity_type: str,
        entity_id: int,
        entity_field: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Optional[Media]:
        """Download image and upload to storage"""
        try:
            # Download image
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Get content type
            content_type = response.headers.get('content-type', 'image/jpeg')

            # Read image data
            image_data = io.BytesIO(response.content)

            # Generate filename
            filename = self._generate_filename(url, 'jpg')

            # Process image (resize, generate thumbnails)
            processed = ImageProcessor.process_image(image_data, filename.rsplit('.', 1)[0])

            # Upload original
            original_url, original_key = await self.storage.save(
                processed['original']['file'],
                processed['original']['filename'],
                content_type
            )

            # Upload variants
            thumbnail_url = None
            medium_url = None
            large_url = None

            if processed['thumbnail']:
                thumbnail_url, _ = await self.storage.save(
                    processed['thumbnail']['file'],
                    processed['thumbnail']['filename'],
                    content_type
                )

            if processed['medium']:
                medium_url, _ = await self.storage.save(
                    processed['medium']['file'],
                    processed['medium']['filename'],
                    content_type
                )

            if processed['large']:
                large_url, _ = await self.storage.save(
                    processed['large']['file'],
                    processed['large']['filename'],
                    content_type
                )

            # Create media record
            media = Media(
                filename=processed['original']['filename'],
                original_filename=filename,
                media_type=MediaType.IMAGE,
                content_type=content_type,
                file_size=len(response.content),
                width=processed['original']['width'],
                height=processed['original']['height'],
                original_url=original_url,
                thumbnail_url=thumbnail_url,
                medium_url=medium_url,
                large_url=large_url,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_field=entity_field,
                caption=caption,
                uploaded_by=self.uploaded_by,
                is_public=True
            )

            self.db.add(media)
            self.db.commit()
            self.db.refresh(media)

            return media

        except Exception as e:
            logger.error(f"❌ Failed to download/upload image {url}: {e}")
            self.db.rollback()
            raise

    async def _download_and_upload_video(
        self,
        url: str,
        entity_type: str,
        entity_id: int,
        entity_field: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Optional[Media]:
        """Download video and upload to storage"""
        # Note: For YouTube/Vimeo, we just save the embed URL
        if 'youtube.com' in url or 'youtu.be' in url or 'vimeo.com' in url:
            return await self._save_video_embed(url, entity_type, entity_id, entity_field, caption)

        try:
            # Download video
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()

            # Get content type
            content_type = response.headers.get('content-type', 'video/mp4')

            # Read video data
            video_data = io.BytesIO(response.content)

            # Generate filename
            filename = self._generate_filename(url, 'mp4')

            # Upload original video
            original_url, original_key = await self.storage.save(
                video_data,
                filename,
                content_type
            )

            # Generate thumbnail
            video_data.seek(0)
            thumbnail_data = VideoProcessor.generate_video_thumbnail(video_data)
            thumbnail_url = None

            if thumbnail_data:
                thumb_filename = f"{filename.rsplit('.', 1)[0]}_thumb.jpg"
                thumbnail_url, _ = await self.storage.save(
                    thumbnail_data,
                    thumb_filename,
                    'image/jpeg'
                )

            # Get video metadata
            video_data.seek(0)
            metadata = VideoProcessor.get_video_metadata(video_data)

            # Create media record
            media = Media(
                filename=filename,
                original_filename=filename,
                media_type=MediaType.VIDEO,
                content_type=content_type,
                file_size=len(response.content),
                width=metadata.get('width'),
                height=metadata.get('height'),
                duration=metadata.get('duration'),
                original_url=original_url,
                thumbnail_url=thumbnail_url,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_field=entity_field,
                caption=caption,
                uploaded_by=self.uploaded_by,
                is_public=True
            )

            self.db.add(media)
            self.db.commit()
            self.db.refresh(media)

            return media

        except Exception as e:
            logger.error(f"❌ Failed to download/upload video {url}: {e}")
            self.db.rollback()
            raise

    async def _save_video_embed(
        self,
        url: str,
        entity_type: str,
        entity_id: int,
        entity_field: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Media:
        """Save video embed URL (YouTube, Vimeo)"""
        media = Media(
            filename="embed_video",
            original_filename=url,
            media_type=MediaType.VIDEO,
            content_type="video/embed",
            file_size=0,
            original_url=url,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_field=entity_field,
            caption=caption,
            uploaded_by=self.uploaded_by,
            is_public=True
        )

        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)

        return media

    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image"""
        # Skip data URLs, tiny images, icons
        if url.startswith('data:'):
            return False

        # Check if it has an image extension
        ext = self._get_file_extension(url)
        if ext not in self.IMAGE_EXTENSIONS:
            return False

        # Skip common icon/logo patterns
        skip_patterns = ['icon', 'logo', 'sprite', 'avatar', 'favicon']
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in skip_patterns):
            return False

        return True

    def _is_valid_video_url(self, url: str) -> bool:
        """Check if URL is a valid video"""
        ext = self._get_file_extension(url)
        return ext in self.VIDEO_EXTENSIONS or 'youtube' in url or 'vimeo' in url

    def _get_file_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        # Parse URL and get path
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Get extension
        if '.' in path:
            ext = '.' + path.rsplit('.', 1)[1].split('?')[0]
            return ext
        return ''

    def _generate_filename(self, url: str, default_ext: str = 'jpg') -> str:
        """Generate a filename from URL"""
        parsed = urlparse(url)
        path = parsed.path

        # Get filename from path
        if path and path != '/':
            filename = path.split('/')[-1]
            if filename and '.' in filename:
                return filename

        # Generate from URL hash
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"scraped_{url_hash}.{default_ext}"
