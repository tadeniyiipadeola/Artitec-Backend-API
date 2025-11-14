"""
Storage abstraction layer for media files.
Supports both local filesystem (development) and S3 (production).
"""

import os
import uuid
from pathlib import Path
from typing import Optional, BinaryIO
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    async def save(self, file_data: BinaryIO, filename: str, content_type: str) -> tuple[str, str]:
        """
        Save file and return (storage_path, access_url)
        """
        pass

    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """
        Delete file from storage
        """
        pass

    @abstractmethod
    def get_url(self, storage_path: str) -> str:
        """
        Get access URL for file
        """
        pass


class LocalFileStorage(StorageBackend):
    """Local filesystem storage for development"""

    def __init__(self, base_dir: str = "uploads", base_url: str = "http://localhost:8000"):
        self.base_dir = Path(base_dir)
        self.base_url = base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalFileStorage initialized: base_dir={self.base_dir}, base_url={self.base_url}")

    async def save(self, file_data: BinaryIO, filename: str, content_type: str) -> tuple[str, str]:
        """
        Save file to local filesystem.
        Returns (storage_path, access_url)
        """
        # Create subdirectories based on file type
        file_ext = Path(filename).suffix.lower()
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            subdir = 'images'
        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
            subdir = 'videos'
        else:
            subdir = 'files'

        target_dir = self.base_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = target_dir / filename
        storage_path = f"{subdir}/{filename}"

        with open(file_path, 'wb') as f:
            content = file_data.read()
            f.write(content)

        access_url = f"{self.base_url}/uploads/{storage_path}"
        logger.info(f"Saved file locally: {storage_path} -> {access_url}")

        return storage_path, access_url

    async def delete(self, storage_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            file_path = self.base_dir / storage_path
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {storage_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {storage_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {storage_path}: {e}")
            return False

    def get_url(self, storage_path: str) -> str:
        """Get access URL for local file"""
        return f"{self.base_url}/uploads/{storage_path}"


class S3Storage(StorageBackend):
    """AWS S3 storage for production"""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,  # For MinIO compatibility
        public_base_url: Optional[str] = None
    ):
        self.bucket_name = bucket_name
        self.region = region
        self.public_base_url = public_base_url

        # Initialize S3 client
        session = boto3.session.Session()
        self.s3_client = session.client(
            's3',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )

        logger.info(f"S3Storage initialized: bucket={bucket_name}, region={region}, endpoint={endpoint_url}")

    async def save(self, file_data: BinaryIO, filename: str, content_type: str) -> tuple[str, str]:
        """
        Upload file to S3.
        Returns (storage_path, access_url)
        """
        # Organize by type
        file_ext = Path(filename).suffix.lower()
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            prefix = 'images'
        elif file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
            prefix = 'videos'
        else:
            prefix = 'files'

        storage_path = f"{prefix}/{filename}"

        try:
            # Upload to S3
            self.s3_client.upload_fileobj(
                file_data,
                self.bucket_name,
                storage_path,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'  # Make publicly accessible
                }
            )

            # Generate access URL
            if self.public_base_url:
                access_url = f"{self.public_base_url}/{storage_path}"
            else:
                access_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{storage_path}"

            logger.info(f"Uploaded to S3: {storage_path} -> {access_url}")
            return storage_path, access_url

        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            raise

    async def delete(self, storage_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=storage_path)
            logger.info(f"Deleted from S3: {storage_path}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting from S3: {e}")
            return False

    def get_url(self, storage_path: str) -> str:
        """Get access URL for S3 object"""
        if self.public_base_url:
            return f"{self.public_base_url}/{storage_path}"
        else:
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{storage_path}"

    def generate_presigned_url(self, storage_path: str, expiration: int = 3600) -> str:
        """Generate presigned URL for temporary access (for private files)"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': storage_path},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise


# Factory function to get storage backend based on environment
def get_storage_backend() -> StorageBackend:
    """
    Get appropriate storage backend based on environment configuration.
    Checks environment variables to determine which backend to use.
    """
    storage_type = os.getenv("STORAGE_TYPE", "local")  # "local" or "s3"

    if storage_type == "s3":
        return S3Storage(
            bucket_name=os.getenv("S3_BUCKET_NAME", "artitec-media"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region=os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),  # For MinIO
            public_base_url=os.getenv("S3_PUBLIC_BASE_URL")
        )
    else:
        # Local filesystem storage
        return LocalFileStorage(
            base_dir=os.getenv("UPLOAD_DIR", "uploads"),
            base_url=os.getenv("BASE_URL", "http://localhost:8000")
        )
