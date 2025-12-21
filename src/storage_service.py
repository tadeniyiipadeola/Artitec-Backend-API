"""
MinIO/S3 storage service for the Artitec platform.
Handles file uploads, downloads, deletion, and presigned URL generation.
"""

import os
import io
from typing import Optional, BinaryIO, Tuple, List, Dict, Any
from datetime import timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
import logging

logger = logging.getLogger(__name__)


class MinIOStorageService:
    """
    MinIO/S3 storage service with comprehensive file operations.
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        region: str = "us-east-1",
        public_base_url: Optional[str] = None,
        secure: bool = True
    ):
        """
        Initialize MinIO storage service.

        Args:
            endpoint_url: MinIO endpoint URL (e.g., 'http://localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket_name: Default bucket name
            region: AWS region (for S3 compatibility)
            public_base_url: Public URL for accessing files
            secure: Whether to use HTTPS
        """
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.region = region
        self.public_base_url = public_base_url
        self.secure = secure

        # Configure boto3 client for MinIO
        config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )

        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=config
            )

            # Ensure bucket exists
            self._ensure_bucket_exists()

            logger.info(
                f"MinIO storage initialized: endpoint={endpoint_url}, "
                f"bucket={bucket_name}, region={region}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise

    def _ensure_bucket_exists(self) -> None:
        """
        Create bucket if it doesn't exist.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise

    def upload_file(
        self,
        file_data: BinaryIO,
        storage_path: str,
        content_type: str = 'application/octet-stream',
        metadata: Optional[Dict[str, str]] = None,
        make_public: bool = True
    ) -> str:
        """
        Upload file to MinIO.

        Args:
            file_data: Binary file data
            storage_path: Storage path/key in bucket
            content_type: MIME type
            metadata: Optional metadata dictionary
            make_public: Whether to make file publicly accessible

        Returns:
            Public URL to access the file

        Raises:
            ClientError: If upload fails
        """
        try:
            extra_args = {
                'ContentType': content_type
            }

            # Add ACL for public access
            if make_public:
                extra_args['ACL'] = 'public-read'

            # Add custom metadata
            if metadata:
                extra_args['Metadata'] = metadata

            # Upload to MinIO
            file_data.seek(0)
            self.s3_client.upload_fileobj(
                file_data,
                self.bucket_name,
                storage_path,
                ExtraArgs=extra_args
            )

            # Generate public URL
            public_url = self.get_public_url(storage_path)

            logger.info(f"Uploaded file to MinIO: {storage_path}")
            return public_url

        except ClientError as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            raise

    def upload_file_from_path(
        self,
        file_path: str,
        storage_path: str,
        content_type: Optional[str] = None,
        make_public: bool = True
    ) -> str:
        """
        Upload file from local path to MinIO.

        Args:
            file_path: Local file path
            storage_path: Storage path/key in bucket
            content_type: MIME type (auto-detected if not provided)
            make_public: Whether to make file publicly accessible

        Returns:
            Public URL to access the file
        """
        try:
            # Auto-detect content type if not provided
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(file_path)
                content_type = content_type or 'application/octet-stream'

            # Upload file
            with open(file_path, 'rb') as f:
                return self.upload_file(f, storage_path, content_type, make_public=make_public)

        except Exception as e:
            logger.error(f"Failed to upload file from path: {e}")
            raise

    def download_file(self, storage_path: str) -> bytes:
        """
        Download file from MinIO.

        Args:
            storage_path: Storage path/key in bucket

        Returns:
            File contents as bytes

        Raises:
            ClientError: If download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            return response['Body'].read()

        except ClientError as e:
            logger.error(f"Failed to download file from MinIO: {e}")
            raise

    def download_file_to_path(self, storage_path: str, local_path: str) -> None:
        """
        Download file from MinIO to local path.

        Args:
            storage_path: Storage path/key in bucket
            local_path: Local destination path

        Raises:
            ClientError: If download fails
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                storage_path,
                local_path
            )

            logger.info(f"Downloaded file from MinIO: {storage_path} -> {local_path}")

        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            raise

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from MinIO.

        Args:
            storage_path: Storage path/key in bucket

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            logger.info(f"Deleted file from MinIO: {storage_path}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    def delete_files(self, storage_paths: List[str]) -> Tuple[int, int]:
        """
        Delete multiple files from MinIO.

        Args:
            storage_paths: List of storage paths/keys

        Returns:
            Tuple of (success_count, fail_count)
        """
        if not storage_paths:
            return 0, 0

        success_count = 0
        fail_count = 0

        # Delete in batches of 1000 (S3 limit)
        batch_size = 1000
        for i in range(0, len(storage_paths), batch_size):
            batch = storage_paths[i:i + batch_size]

            try:
                objects = [{'Key': path} for path in batch]
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects}
                )

                deleted = response.get('Deleted', [])
                errors = response.get('Errors', [])

                success_count += len(deleted)
                fail_count += len(errors)

                if errors:
                    for error in errors:
                        logger.warning(f"Failed to delete {error['Key']}: {error.get('Message')}")

            except ClientError as e:
                logger.error(f"Batch delete failed: {e}")
                fail_count += len(batch)

        logger.info(f"Batch deleted files: {success_count} succeeded, {fail_count} failed")
        return success_count, fail_count

    def file_exists(self, storage_path: str) -> bool:
        """
        Check if file exists in MinIO.

        Args:
            storage_path: Storage path/key in bucket

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            logger.error(f"Error checking file existence: {e}")
            return False

    def get_file_info(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from MinIO.

        Args:
            storage_path: Storage path/key in bucket

        Returns:
            Dictionary with file info or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )

            return {
                'size': response['ContentLength'],
                'content_type': response.get('ContentType'),
                'last_modified': response['LastModified'],
                'etag': response['ETag'].strip('"'),
                'metadata': response.get('Metadata', {})
            }

        except ClientError as e:
            logger.error(f"Failed to get file info: {e}")
            return None

    def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List files in bucket with optional prefix filter.

        Args:
            prefix: Prefix filter (folder path)
            max_keys: Maximum number of keys to return

        Returns:
            List of file information dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                })

            logger.info(f"Listed {len(files)} files with prefix '{prefix}'")
            return files

        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def generate_presigned_url(
        self,
        storage_path: str,
        expiration: int = 3600,
        method: str = 'get_object'
    ) -> Optional[str]:
        """
        Generate presigned URL for temporary access.

        Args:
            storage_path: Storage path/key in bucket
            expiration: URL expiration time in seconds (default: 1 hour)
            method: S3 method ('get_object' for download, 'put_object' for upload)

        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': storage_path
                },
                ExpiresIn=expiration
            )

            logger.info(f"Generated presigned URL for {storage_path} (expires in {expiration}s)")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def get_public_url(self, storage_path: str) -> str:
        """
        Get public URL for accessing file.

        Args:
            storage_path: Storage path/key in bucket

        Returns:
            Public URL
        """
        if self.public_base_url:
            # Use custom public base URL
            return f"{self.public_base_url.rstrip('/')}/{storage_path}"
        else:
            # Use MinIO endpoint URL
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{storage_path}"

    def copy_file(
        self,
        source_path: str,
        dest_path: str,
        source_bucket: Optional[str] = None
    ) -> bool:
        """
        Copy file within MinIO.

        Args:
            source_path: Source storage path
            dest_path: Destination storage path
            source_bucket: Source bucket (uses default if not specified)

        Returns:
            True if successful, False otherwise
        """
        try:
            source_bucket = source_bucket or self.bucket_name

            copy_source = {
                'Bucket': source_bucket,
                'Key': source_path
            }

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_path
            )

            logger.info(f"Copied file: {source_path} -> {dest_path}")
            return True

        except ClientError as e:
            logger.error(f"Failed to copy file: {e}")
            return False

    def get_bucket_size(self) -> Dict[str, Any]:
        """
        Calculate total size and file count in bucket.

        Returns:
            Dictionary with total_size_bytes, total_files
        """
        try:
            total_size = 0
            total_files = 0

            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)

            for page in pages:
                for obj in page.get('Contents', []):
                    total_size += obj['Size']
                    total_files += 1

            return {
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
                'total_files': total_files
            }

        except ClientError as e:
            logger.error(f"Failed to calculate bucket size: {e}")
            return {
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'total_size_gb': 0,
                'total_files': 0
            }

    def create_bucket(self, bucket_name: str) -> bool:
        """
        Create a new bucket.

        Args:
            bucket_name: Name of bucket to create

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created bucket: {bucket_name}")
            return True

        except ClientError as e:
            logger.error(f"Failed to create bucket: {e}")
            return False

    def delete_bucket(self, bucket_name: str, force: bool = False) -> bool:
        """
        Delete a bucket.

        Args:
            bucket_name: Name of bucket to delete
            force: If True, delete all objects first

        Returns:
            True if successful, False otherwise
        """
        try:
            if force:
                # Delete all objects first
                paginator = self.s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket_name)

                for page in pages:
                    objects = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
                    if objects:
                        self.s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': objects}
                        )

            # Delete bucket
            self.s3_client.delete_bucket(Bucket=bucket_name)
            logger.info(f"Deleted bucket: {bucket_name}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete bucket: {e}")
            return False


def get_minio_service() -> MinIOStorageService:
    """
    Factory function to create MinIO service from environment variables.

    Returns:
        Configured MinIOStorageService instance
    """
    return MinIOStorageService(
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://localhost:9000"),
        access_key=os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"),
        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin"),
        bucket_name=os.getenv("S3_BUCKET_NAME", "artitec-media"),
        region=os.getenv("AWS_REGION", "us-east-1"),
        public_base_url=os.getenv("S3_PUBLIC_BASE_URL"),
        secure=os.getenv("S3_SECURE", "true").lower() == "true"
    )


# Global instance for easy importing
storage_service = get_minio_service()
