"""
Media configuration for the Artitec platform.
Defines allowed file types, size limits, thumbnail configurations, and storage settings.
"""

import os
from typing import Dict, List, Tuple
from pathlib import Path


class MediaConfig:
    """
    Centralized media configuration.
    """

    # ============================================================================
    # FILE TYPE CONFIGURATIONS
    # ============================================================================

    # Allowed image MIME types and extensions
    ALLOWED_IMAGE_TYPES: Dict[str, List[str]] = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/webp': ['.webp'],
        'image/bmp': ['.bmp'],
        'image/tiff': ['.tiff', '.tif']
    }

    # Allowed video MIME types and extensions
    ALLOWED_VIDEO_TYPES: Dict[str, List[str]] = {
        'video/mp4': ['.mp4'],
        'video/quicktime': ['.mov'],
        'video/x-msvideo': ['.avi'],
        'video/x-matroska': ['.mkv'],
        'video/webm': ['.webm'],
        'video/x-m4v': ['.m4v']
    }

    # ============================================================================
    # FILE SIZE LIMITS (in bytes)
    # ============================================================================

    # Image size limits
    MAX_IMAGE_SIZE: int = 20 * 1024 * 1024  # 20 MB
    MIN_IMAGE_SIZE: int = 1024  # 1 KB

    # Video size limits
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024  # 500 MB
    MIN_VIDEO_SIZE: int = 10 * 1024  # 10 KB

    # Avatar/profile photo size limits
    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024  # 5 MB

    # ============================================================================
    # DIMENSION LIMITS
    # ============================================================================

    # Image dimensions
    MAX_IMAGE_DIMENSION: int = 8000  # 8000 x 8000 pixels max
    MIN_IMAGE_DIMENSION: int = 50    # 50 x 50 pixels min

    # Avatar/profile photo dimensions
    MIN_AVATAR_DIMENSION: int = 100  # 100 x 100 pixels min
    MAX_AVATAR_DIMENSION: int = 2000  # 2000 x 2000 pixels max

    # ============================================================================
    # THUMBNAIL CONFIGURATIONS
    # ============================================================================

    # Thumbnail sizes (width, height)
    THUMBNAIL_SMALL: Tuple[int, int] = (150, 150)
    THUMBNAIL_MEDIUM: Tuple[int, int] = (400, 400)
    THUMBNAIL_LARGE: Tuple[int, int] = (800, 800)

    # Image resize configurations
    IMAGE_SIZES: Dict[str, Tuple[int, int]] = {
        'thumbnail': (150, 150),
        'small': (400, 400),
        'medium': (800, 800),
        'large': (1600, 1600),
    }

    # JPEG quality settings
    THUMBNAIL_QUALITY: int = 80
    SMALL_QUALITY: int = 85
    MEDIUM_QUALITY: int = 85
    LARGE_QUALITY: int = 90

    # ============================================================================
    # STORAGE PATH STRUCTURE
    # ============================================================================

    # Storage path template: {entity_type}s/{media_type}/{entity_id}/{YYYY-MM}/{filename}
    # Examples:
    #   - properties/photos/PROP-123/2023-11/photo-20231120-abc123.jpg
    #   - communities/gallery/CMY-456/2023-11/gallery-20231120-def456.jpg
    #   - users/avatar/USR-789/2023-11/avatar-20231120-ghi789.jpg

    STORAGE_PATH_TEMPLATE: str = "{entity_type}s/{media_type}/{entity_id}/{year_month}/{filename}"

    # Entity type mappings (singular -> plural)
    ENTITY_TYPE_FOLDERS: Dict[str, str] = {
        'property': 'properties',
        'community': 'communities',
        'user': 'users',
        'builder': 'builders',
        'sales_rep': 'sales_reps',
        'post': 'posts',
        'amenity': 'amenities',
        'event': 'events',
    }

    # Media type folder names
    MEDIA_TYPE_FOLDERS: Dict[str, str] = {
        'avatar': 'avatars',
        'cover': 'covers',
        'gallery': 'photos',
        'video_intro': 'videos',
        'thumbnail': 'thumbnails',
        'amenities': 'amenities',
    }

    # ============================================================================
    # FILENAME GENERATION
    # ============================================================================

    # Filename template: {media_type}-{timestamp}-{random}.{ext}
    # Example: photo-20231120153045-a1b2c3.jpg
    FILENAME_TEMPLATE: str = "{media_type}-{timestamp}-{random}{ext}"

    # Random suffix length for uniqueness
    RANDOM_SUFFIX_LENGTH: int = 6

    # ============================================================================
    # MINIO/S3 SETTINGS
    # ============================================================================

    @staticmethod
    def get_storage_config() -> Dict[str, any]:
        """
        Get storage configuration from environment variables.

        Returns:
            Dictionary with storage configuration
        """
        return {
            'storage_type': os.getenv('STORAGE_TYPE', 'local'),
            's3_endpoint_url': os.getenv('S3_ENDPOINT_URL', 'http://localhost:9000'),
            's3_access_key': os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
            's3_secret_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin'),
            's3_bucket_name': os.getenv('S3_BUCKET_NAME', 'artitec-media'),
            's3_region': os.getenv('AWS_REGION', 'us-east-1'),
            's3_public_base_url': os.getenv('S3_PUBLIC_BASE_URL'),
            's3_secure': os.getenv('S3_SECURE', 'true').lower() == 'true',
            'local_upload_dir': os.getenv('UPLOAD_DIR', 'uploads'),
            'base_url': os.getenv('BASE_URL', 'http://localhost:8000'),
        }

    # ============================================================================
    # DUPLICATE DETECTION SETTINGS
    # ============================================================================

    # Perceptual hash similarity threshold
    # Lower value = more strict (only exact matches)
    # Higher value = more lenient (similar images)
    DUPLICATE_HASH_THRESHOLD: int = 5

    # ============================================================================
    # VIDEO PROCESSING SETTINGS
    # ============================================================================

    # Video thumbnail extraction settings
    VIDEO_THUMBNAIL_TIMESTAMP: int = 1  # Extract frame at 1 second
    VIDEO_THUMBNAIL_SIZE: Tuple[int, int] = (150, 150)

    # Video compression settings
    VIDEO_COMPRESSION_PRESETS: Dict[str, Dict[str, any]] = {
        '480p': {
            'scale': 'scale=-2:480',
            'crf': 23,
            'preset': 'medium',
        },
        '720p': {
            'scale': 'scale=-2:720',
            'crf': 23,
            'preset': 'medium',
        },
        '1080p': {
            'scale': 'scale=-2:1080',
            'crf': 23,
            'preset': 'medium',
        },
    }

    # Default video compression preset
    DEFAULT_VIDEO_PRESET: str = '720p'

    # ============================================================================
    # BATCH UPLOAD SETTINGS
    # ============================================================================

    # Maximum files per batch upload
    MAX_BATCH_UPLOAD_SIZE: int = 20

    # Maximum concurrent uploads
    MAX_CONCURRENT_UPLOADS: int = 5

    # ============================================================================
    # CONTENT MODERATION SETTINGS
    # ============================================================================

    # Auto-approve uploads from verified users
    AUTO_APPROVE_VERIFIED_USERS: bool = True

    # Auto-approve uploads from certain entity types
    AUTO_APPROVE_ENTITY_TYPES: List[str] = ['user', 'builder', 'community', 'sales_rep']

    # Require manual moderation for these entity types
    REQUIRE_MODERATION_ENTITY_TYPES: List[str] = ['post']

    # ============================================================================
    # EXIF DATA SETTINGS
    # ============================================================================

    # EXIF tags to extract and store
    EXIF_TAGS_TO_EXTRACT: List[str] = [
        'Make',  # Camera make
        'Model',  # Camera model
        'DateTime',  # Date/time original
        'DateTimeOriginal',
        'DateTimeDigitized',
        'ExposureTime',
        'FNumber',
        'ISO',
        'Flash',
        'FocalLength',
        'LensModel',
        'GPSLatitude',
        'GPSLongitude',
        'GPSAltitude',
        'Orientation',
        'Copyright',
        'Artist',
    ]

    # Strip GPS data for privacy
    STRIP_GPS_DATA: bool = True

    # ============================================================================
    # CACHING SETTINGS
    # ============================================================================

    # Cache control headers for media files
    CACHE_CONTROL_IMAGES: str = 'public, max-age=31536000, immutable'  # 1 year
    CACHE_CONTROL_VIDEOS: str = 'public, max-age=31536000, immutable'  # 1 year

    # CDN URL (if using CDN)
    CDN_URL: str = os.getenv('CDN_URL', '')

    # ============================================================================
    # CLEANUP SETTINGS
    # ============================================================================

    # Auto-delete unapproved media after N days
    AUTO_DELETE_UNAPPROVED_DAYS: int = 7

    # Keep deleted media in trash for N days before permanent deletion
    TRASH_RETENTION_DAYS: int = 30

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    @staticmethod
    def get_allowed_extensions() -> List[str]:
        """Get list of all allowed file extensions."""
        extensions = []
        for exts in MediaConfig.ALLOWED_IMAGE_TYPES.values():
            extensions.extend(exts)
        for exts in MediaConfig.ALLOWED_VIDEO_TYPES.values():
            extensions.extend(exts)
        return extensions

    @staticmethod
    def is_image_extension(filename: str) -> bool:
        """Check if filename has an image extension."""
        ext = Path(filename).suffix.lower()
        return ext in [e for exts in MediaConfig.ALLOWED_IMAGE_TYPES.values() for e in exts]

    @staticmethod
    def is_video_extension(filename: str) -> bool:
        """Check if filename has a video extension."""
        ext = Path(filename).suffix.lower()
        return ext in [e for exts in MediaConfig.ALLOWED_VIDEO_TYPES.values() for e in exts]

    @staticmethod
    def get_size_limit(media_type: str, entity_field: str = None) -> int:
        """
        Get size limit for media type.

        Args:
            media_type: 'image' or 'video'
            entity_field: Optional entity field (e.g., 'avatar')

        Returns:
            Size limit in bytes
        """
        if entity_field == 'avatar':
            return MediaConfig.MAX_AVATAR_SIZE

        if media_type == 'image':
            return MediaConfig.MAX_IMAGE_SIZE
        elif media_type == 'video':
            return MediaConfig.MAX_VIDEO_SIZE

        return MediaConfig.MAX_IMAGE_SIZE

    @staticmethod
    def get_storage_path_pattern(
        entity_type: str,
        media_type: str,
        entity_id: str
    ) -> str:
        """
        Generate storage path pattern.

        Args:
            entity_type: Entity type (property, community, etc.)
            media_type: Media type (avatar, gallery, etc.)
            entity_id: Entity ID

        Returns:
            Storage path pattern
        """
        from datetime import datetime

        entity_folder = MediaConfig.ENTITY_TYPE_FOLDERS.get(entity_type, f"{entity_type}s")
        media_folder = MediaConfig.MEDIA_TYPE_FOLDERS.get(media_type, media_type)
        year_month = datetime.now().strftime("%Y-%m")

        return f"{entity_folder}/{media_folder}/{entity_id}/{year_month}"


# Export configuration as module-level constants for easy import
ALLOWED_IMAGE_TYPES = MediaConfig.ALLOWED_IMAGE_TYPES
ALLOWED_VIDEO_TYPES = MediaConfig.ALLOWED_VIDEO_TYPES
MAX_IMAGE_SIZE = MediaConfig.MAX_IMAGE_SIZE
MAX_VIDEO_SIZE = MediaConfig.MAX_VIDEO_SIZE
THUMBNAIL_SIZES = MediaConfig.IMAGE_SIZES
STORAGE_CONFIG = MediaConfig.get_storage_config()
