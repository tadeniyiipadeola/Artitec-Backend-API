"""
Enhanced media processing utilities for the Artitec platform.
Handles file validation, image processing, thumbnail generation, EXIF extraction, and duplicate detection.
"""

import os
import io
import hashlib
import uuid
from pathlib import Path
from typing import Optional, BinaryIO, Tuple, Dict, Any, List
from datetime import datetime
from PIL import Image, ImageFile
from PIL.ExifTags import TAGS
import imagehash
import logging

logger = logging.getLogger(__name__)

# Allow loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True


class MediaValidator:
    """
    Media file validator for type checking and size limits.
    """

    # File type configurations
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/webp': ['.webp'],
        'image/bmp': ['.bmp'],
        'image/tiff': ['.tiff', '.tif']
    }

    ALLOWED_VIDEO_TYPES = {
        'video/mp4': ['.mp4'],
        'video/quicktime': ['.mov'],
        'video/x-msvideo': ['.avi'],
        'video/x-matroska': ['.mkv'],
        'video/webm': ['.webm'],
        'video/x-m4v': ['.m4v']
    }

    # Size limits (in bytes)
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB

    # Dimension limits
    MAX_IMAGE_DIMENSION = 8000  # 8000 x 8000 pixels max
    MIN_IMAGE_DIMENSION = 50   # 50 x 50 pixels min

    @classmethod
    def validate_file(
        cls,
        filename: str,
        file_size: int,
        content_type: Optional[str] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        Validate uploaded file.

        Args:
            filename: Original filename
            file_size: File size in bytes
            content_type: MIME type

        Returns:
            Tuple of (is_valid, error_message, media_type)
            media_type will be 'image' or 'video'
        """
        ext = Path(filename).suffix.lower()

        # Check if it's an image
        if content_type in cls.ALLOWED_IMAGE_TYPES or ext in [e for exts in cls.ALLOWED_IMAGE_TYPES.values() for e in exts]:
            if file_size > cls.MAX_IMAGE_SIZE:
                return False, f"Image file too large. Maximum size is {cls.MAX_IMAGE_SIZE // (1024*1024)} MB", "image"
            return True, None, "image"

        # Check if it's a video
        if content_type in cls.ALLOWED_VIDEO_TYPES or ext in [e for exts in cls.ALLOWED_VIDEO_TYPES.values() for e in exts]:
            if file_size > cls.MAX_VIDEO_SIZE:
                return False, f"Video file too large. Maximum size is {cls.MAX_VIDEO_SIZE // (1024*1024)} MB", "video"
            return True, None, "video"

        return False, f"Unsupported file type: {ext}. Allowed types: {', '.join([e for exts in cls.ALLOWED_IMAGE_TYPES.values() for e in exts] + [e for exts in cls.ALLOWED_VIDEO_TYPES.values() for e in exts])}", "unknown"

    @classmethod
    def validate_image_dimensions(cls, width: int, height: int) -> Tuple[bool, Optional[str]]:
        """
        Validate image dimensions.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if width > cls.MAX_IMAGE_DIMENSION or height > cls.MAX_IMAGE_DIMENSION:
            return False, f"Image dimensions too large. Maximum: {cls.MAX_IMAGE_DIMENSION}x{cls.MAX_IMAGE_DIMENSION}"

        if width < cls.MIN_IMAGE_DIMENSION or height < cls.MIN_IMAGE_DIMENSION:
            return False, f"Image dimensions too small. Minimum: {cls.MIN_IMAGE_DIMENSION}x{cls.MIN_IMAGE_DIMENSION}"

        return True, None


class ImageProcessorEnhanced:
    """
    Enhanced image processing with EXIF extraction and perceptual hashing.
    """

    # Thumbnail configurations
    THUMBNAIL_SMALL = (150, 150)
    THUMBNAIL_MEDIUM = (400, 400)
    THUMBNAIL_LARGE = (800, 800)

    @staticmethod
    def extract_exif_data(img: Image.Image) -> Dict[str, Any]:
        """
        Extract EXIF metadata from image.

        Args:
            img: PIL Image object

        Returns:
            Dictionary of EXIF data
        """
        exif_data = {}

        try:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)

                    # Convert bytes to string
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = str(value)

                    # Skip large binary data
                    if isinstance(value, (str, int, float)):
                        exif_data[tag] = value

                logger.info(f"Extracted {len(exif_data)} EXIF fields")
        except Exception as e:
            logger.warning(f"Error extracting EXIF data: {e}")

        return exif_data

    @staticmethod
    def calculate_perceptual_hash(img: Image.Image) -> str:
        """
        Calculate perceptual hash for duplicate detection.

        Args:
            img: PIL Image object

        Returns:
            Hex string of perceptual hash
        """
        try:
            # Use average hash (fast and good for finding near-duplicates)
            hash_value = imagehash.average_hash(img)
            return str(hash_value)
        except Exception as e:
            logger.error(f"Error calculating perceptual hash: {e}")
            return ""

    @staticmethod
    def fix_orientation(img: Image.Image) -> Image.Image:
        """
        Fix image orientation based on EXIF data.

        Args:
            img: PIL Image object

        Returns:
            Rotated image if needed
        """
        try:
            exif = img._getexif()
            if exif is not None:
                orientation = exif.get(274)  # 274 is the orientation tag

                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)

                logger.debug(f"Fixed image orientation: {orientation}")
        except (AttributeError, KeyError, IndexError, TypeError):
            # No EXIF data or orientation tag
            pass

        return img

    @staticmethod
    def resize_image(
        img: Image.Image,
        max_size: Tuple[int, int],
        quality: int = 85,
        format: str = "JPEG"
    ) -> BinaryIO:
        """
        Resize image maintaining aspect ratio.

        Args:
            img: PIL Image object
            max_size: Maximum dimensions (width, height)
            quality: JPEG quality (1-100)
            format: Output format

        Returns:
            BytesIO object with resized image
        """
        try:
            # Fix orientation first
            img = ImageProcessorEnhanced.fix_orientation(img)

            # Convert RGBA to RGB for JPEG
            if format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            # Resize maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save to BytesIO
            output = io.BytesIO()
            img.save(output, format=format, quality=quality, optimize=True)
            output.seek(0)

            logger.info(f"Resized image to {img.size} ({format}, quality={quality})")
            return output

        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            raise

    @staticmethod
    def generate_thumbnail(
        img: Image.Image,
        size: Tuple[int, int] = (150, 150),
        crop_to_square: bool = True
    ) -> BinaryIO:
        """
        Generate thumbnail image.

        Args:
            img: PIL Image object
            size: Thumbnail size
            crop_to_square: Whether to crop to square

        Returns:
            BytesIO object with thumbnail
        """
        try:
            # Fix orientation
            img = ImageProcessorEnhanced.fix_orientation(img)

            # Convert to RGB
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            # Crop to square if requested
            if crop_to_square:
                width, height = img.size
                if width > height:
                    left = (width - height) / 2
                    img = img.crop((left, 0, left + height, height))
                elif height > width:
                    top = (height - width) / 2
                    img = img.crop((0, top, width, top + width))

            # Resize
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Save
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=80, optimize=True)
            output.seek(0)

            logger.info(f"Generated thumbnail: {img.size}")
            return output

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            raise

    @staticmethod
    def process_image_complete(
        file_data: BinaryIO,
        generate_sizes: List[str] = ["thumbnail", "small", "medium", "large"]
    ) -> Dict[str, Any]:
        """
        Complete image processing pipeline.

        Args:
            file_data: Binary image data
            generate_sizes: List of sizes to generate

        Returns:
            Dictionary containing processed images and metadata
        """
        result = {
            'original': None,
            'thumbnail': None,
            'small': None,
            'medium': None,
            'large': None,
            'metadata': {},
            'perceptual_hash': None,
            'dimensions': (0, 0)
        }

        try:
            # Load image
            img = Image.open(file_data)
            original_width, original_height = img.size
            result['dimensions'] = (original_width, original_height)

            # Extract EXIF
            if "exif" in generate_sizes or True:  # Always extract EXIF
                result['metadata'] = ImageProcessorEnhanced.extract_exif_data(img)

            # Calculate perceptual hash
            result['perceptual_hash'] = ImageProcessorEnhanced.calculate_perceptual_hash(img)

            # Store original
            file_data.seek(0)
            result['original'] = file_data

            # Generate thumbnail (square crop)
            if "thumbnail" in generate_sizes:
                result['thumbnail'] = ImageProcessorEnhanced.generate_thumbnail(
                    img.copy(),
                    ImageProcessorEnhanced.THUMBNAIL_SMALL,
                    crop_to_square=True
                )

            # Generate small size
            if "small" in generate_sizes and (original_width > 150 or original_height > 150):
                result['small'] = ImageProcessorEnhanced.resize_image(
                    img.copy(),
                    ImageProcessorEnhanced.THUMBNAIL_SMALL,
                    quality=85
                )

            # Generate medium size
            if "medium" in generate_sizes and (original_width > 400 or original_height > 400):
                result['medium'] = ImageProcessorEnhanced.resize_image(
                    img.copy(),
                    ImageProcessorEnhanced.THUMBNAIL_MEDIUM,
                    quality=85
                )

            # Generate large size
            if "large" in generate_sizes and (original_width > 800 or original_height > 800):
                result['large'] = ImageProcessorEnhanced.resize_image(
                    img.copy(),
                    ImageProcessorEnhanced.THUMBNAIL_LARGE,
                    quality=90
                )

            logger.info(
                f"Processed image: {original_width}x{original_height}, "
                f"generated {len([k for k, v in result.items() if v and k not in ['metadata', 'perceptual_hash', 'dimensions']])} variants"
            )

        except Exception as e:
            logger.error(f"Error in complete image processing: {e}")
            raise

        return result


class PathGenerator:
    """
    Generate organized storage paths for media files.
    """

    @staticmethod
    def generate_unique_filename(
        original_filename: str,
        media_type: str,
        prefix: str = ""
    ) -> str:
        """
        Generate unique filename.

        Format: {media_type}-{timestamp}-{random}.{ext}
        Example: photo-20231120153045-a1b2c3.jpg

        Args:
            original_filename: Original uploaded filename
            media_type: Type of media (photo, video, avatar, etc.)
            prefix: Optional prefix

        Returns:
            Unique filename
        """
        ext = Path(original_filename).suffix.lower()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = uuid.uuid4().hex[:6]

        if prefix:
            return f"{prefix}-{media_type}-{timestamp}-{random_suffix}{ext}"
        else:
            return f"{media_type}-{timestamp}-{random_suffix}{ext}"

    @staticmethod
    def generate_storage_path(
        entity_type: str,
        media_type: str,
        entity_id: str,
        filename: str
    ) -> str:
        """
        Generate organized storage path.

        Format: {entity_type}s/{media_type}/{entity_id}/{YYYY-MM}/{filename}
        Example: properties/photos/PROP-123/2023-11/photo-20231120-abc123.jpg

        Args:
            entity_type: Type of entity (property, community, user, etc.)
            media_type: Type of media (photos, videos, avatars, etc.)
            entity_id: Entity ID (public_id or profile_id)
            filename: Generated filename

        Returns:
            Storage path
        """
        year_month = datetime.now().strftime("%Y-%m")

        # Pluralize entity type if needed
        entity_folder = f"{entity_type}s" if not entity_type.endswith('s') else entity_type

        return f"{entity_folder}/{media_type}/{entity_id}/{year_month}/{filename}"


class DuplicateDetector:
    """
    Detect duplicate media using perceptual hashing.
    """

    @staticmethod
    def calculate_hash_distance(hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two perceptual hashes.

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Hamming distance (0 = identical, higher = more different)
        """
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except:
            return 999  # Return high distance on error

    @staticmethod
    def is_duplicate(hash1: str, hash2: str, threshold: int = 5) -> bool:
        """
        Check if two images are likely duplicates.

        Args:
            hash1: First perceptual hash
            hash2: Second perceptual hash
            threshold: Maximum distance to consider duplicate (default: 5)

        Returns:
            True if likely duplicates
        """
        distance = DuplicateDetector.calculate_hash_distance(hash1, hash2)
        return distance <= threshold


class FileHasher:
    """
    Calculate file hashes for integrity and deduplication.
    """

    @staticmethod
    def calculate_md5(file_data: BinaryIO) -> str:
        """
        Calculate MD5 hash of file.

        Args:
            file_data: Binary file data

        Returns:
            Hexadecimal MD5 hash
        """
        md5_hash = hashlib.md5()

        file_data.seek(0)
        for chunk in iter(lambda: file_data.read(4096), b''):
            md5_hash.update(chunk)
        file_data.seek(0)

        return md5_hash.hexdigest()

    @staticmethod
    def calculate_sha256(file_data: BinaryIO) -> str:
        """
        Calculate SHA256 hash of file.

        Args:
            file_data: Binary file data

        Returns:
            Hexadecimal SHA256 hash
        """
        sha256_hash = hashlib.sha256()

        file_data.seek(0)
        for chunk in iter(lambda: file_data.read(4096), b''):
            sha256_hash.update(chunk)
        file_data.seek(0)

        return sha256_hash.hexdigest()
