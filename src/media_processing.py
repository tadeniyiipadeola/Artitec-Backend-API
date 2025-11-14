"""
Media processing services for images and videos.
Handles thumbnail generation, resizing, format conversion, and optimization.
"""

import os
import io
import uuid
import subprocess
from pathlib import Path
from typing import Optional, BinaryIO, Tuple
from PIL import Image
from PIL.ExifTags import TAGS
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processing service using Pillow"""

    # Standard sizes for processed images
    THUMBNAIL_SIZE = (150, 150)
    MEDIUM_SIZE = (800, 800)
    LARGE_SIZE = (1600, 1600)

    # Supported formats
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    @staticmethod
    def is_supported(filename: str) -> bool:
        """Check if file format is supported"""
        ext = Path(filename).suffix.lower()
        return ext in ImageProcessor.SUPPORTED_FORMATS

    @staticmethod
    def get_image_dimensions(file_data: BinaryIO) -> Tuple[int, int]:
        """Get image dimensions without fully loading"""
        try:
            img = Image.open(file_data)
            width, height = img.size
            file_data.seek(0)  # Reset file pointer
            return width, height
        except Exception as e:
            logger.error(f"Error getting image dimensions: {e}")
            file_data.seek(0)
            return 0, 0

    @staticmethod
    def fix_orientation(img: Image.Image) -> Image.Image:
        """Fix image orientation based on EXIF data"""
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
        except (AttributeError, KeyError, IndexError):
            # No EXIF data or orientation tag
            pass
        return img

    @staticmethod
    def resize_image(
        file_data: BinaryIO,
        max_size: Tuple[int, int],
        quality: int = 85,
        format: str = "JPEG"
    ) -> BinaryIO:
        """
        Resize image maintaining aspect ratio.
        Returns a new BytesIO object with resized image.
        """
        try:
            img = Image.open(file_data)
            img = ImageProcessor.fix_orientation(img)

            # Convert RGBA to RGB for JPEG
            if format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
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
            file_data.seek(0)
            return file_data

    @staticmethod
    def generate_thumbnail(file_data: BinaryIO) -> BinaryIO:
        """Generate square thumbnail (150x150)"""
        try:
            img = Image.open(file_data)
            img = ImageProcessor.fix_orientation(img)

            # Convert to RGB if needed
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            # Create square thumbnail with cropping
            width, height = img.size
            if width > height:
                left = (width - height) / 2
                img = img.crop((left, 0, left + height, height))
            elif height > width:
                top = (height - width) / 2
                img = img.crop((0, top, width, top + width))

            img.thumbnail(ImageProcessor.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Save to BytesIO
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=80, optimize=True)
            output.seek(0)

            logger.info(f"Generated thumbnail: {img.size}")
            return output

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            file_data.seek(0)
            return file_data

    @staticmethod
    def process_image(file_data: BinaryIO, base_filename: str) -> dict:
        """
        Process image and generate all sizes.
        Returns dict with file info for each size variant.
        """
        result = {
            'original': None,
            'thumbnail': None,
            'medium': None,
            'large': None
        }

        try:
            # Get dimensions
            width, height = ImageProcessor.get_image_dimensions(file_data)

            # Store original
            file_data.seek(0)
            result['original'] = {
                'file': file_data,
                'filename': f"{base_filename}.jpg",
                'width': width,
                'height': height
            }

            # Generate thumbnail (always)
            thumbnail_data = ImageProcessor.generate_thumbnail(file_data)
            if thumbnail_data:
                thumb_width, thumb_height = ImageProcessor.get_image_dimensions(thumbnail_data)
                result['thumbnail'] = {
                    'file': thumbnail_data,
                    'filename': f"{base_filename}_thumbnail.jpg",
                    'width': thumb_width,
                    'height': thumb_height
                }

            # Generate medium size if original is larger
            if width > ImageProcessor.MEDIUM_SIZE[0] or height > ImageProcessor.MEDIUM_SIZE[1]:
                medium_data = ImageProcessor.resize_image(
                    file_data,
                    ImageProcessor.MEDIUM_SIZE,
                    quality=85
                )
                if medium_data:
                    med_width, med_height = ImageProcessor.get_image_dimensions(medium_data)
                    result['medium'] = {
                        'file': medium_data,
                        'filename': f"{base_filename}_medium.jpg",
                        'width': med_width,
                        'height': med_height
                    }

            # Generate large size if original is larger
            if width > ImageProcessor.LARGE_SIZE[0] or height > ImageProcessor.LARGE_SIZE[1]:
                large_data = ImageProcessor.resize_image(
                    file_data,
                    ImageProcessor.LARGE_SIZE,
                    quality=90
                )
                if large_data:
                    large_width, large_height = ImageProcessor.get_image_dimensions(large_data)
                    result['large'] = {
                        'file': large_data,
                        'filename': f"{base_filename}_large.jpg",
                        'width': large_width,
                        'height': large_height
                    }

            logger.info(f"Processed image: original={width}x{height}, generated {len([k for k, v in result.items() if v])} variants")

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            # Return at least the original
            file_data.seek(0)
            result['original'] = {
                'file': file_data,
                'filename': f"{base_filename}.jpg",
                'width': 0,
                'height': 0
            }

        return result


class VideoProcessor:
    """Video processing service using ffmpeg"""

    SUPPORTED_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.webm'}

    @staticmethod
    def is_supported(filename: str) -> bool:
        """Check if video format is supported"""
        ext = Path(filename).suffix.lower()
        return ext in VideoProcessor.SUPPORTED_FORMATS

    @staticmethod
    def get_video_metadata(file_path: str) -> dict:
        """
        Get video metadata using ffprobe.
        Returns dict with width, height, duration, etc.
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)

                # Find video stream
                video_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'video'), None)

                if video_stream:
                    return {
                        'width': int(video_stream.get('width', 0)),
                        'height': int(video_stream.get('height', 0)),
                        'duration': int(float(data.get('format', {}).get('duration', 0))),
                        'codec': video_stream.get('codec_name', 'unknown')
                    }
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")

        return {'width': 0, 'height': 0, 'duration': 0, 'codec': 'unknown'}

    @staticmethod
    def generate_video_thumbnail(input_path: str, output_path: str, timestamp: int = 1) -> bool:
        """
        Generate thumbnail from video at specific timestamp.
        Returns True if successful.
        """
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),  # Seek to timestamp
                '-i', input_path,
                '-vframes', '1',  # Extract 1 frame
                '-q:v', '2',  # Quality
                '-vf', 'scale=150:150:force_original_aspect_ratio=increase,crop=150:150',  # Square thumbnail
                '-y',  # Overwrite
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Generated video thumbnail: {output_path}")
                return True
            else:
                logger.error(f"Error generating video thumbnail: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error generating video thumbnail: {e}")
            return False

    @staticmethod
    def compress_video(input_path: str, output_path: str, target_size: str = "720p") -> bool:
        """
        Compress/transcode video for web delivery.
        target_size: "480p", "720p", "1080p"
        Returns True if successful.
        """
        try:
            # Determine scale based on target size
            scale_map = {
                "480p": "scale=-2:480",
                "720p": "scale=-2:720",
                "1080p": "scale=-2:1080"
            }
            scale = scale_map.get(target_size, "scale=-2:720")

            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vcodec', 'libx264',  # H.264 codec
                '-preset', 'medium',  # Encoding speed/quality tradeoff
                '-crf', '23',  # Quality (lower = better, 18-28 is good range)
                '-vf', scale,  # Scale video
                '-acodec', 'aac',  # Audio codec
                '-b:a', '128k',  # Audio bitrate
                '-movflags', '+faststart',  # Enable streaming
                '-y',  # Overwrite
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Compressed video: {output_path}")
                return True
            else:
                logger.error(f"Error compressing video: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error compressing video: {e}")
            return False
