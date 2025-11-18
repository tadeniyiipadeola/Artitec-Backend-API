"""
Storage Migration Tool - Migrate media files from local storage to MinIO/S3

This script migrates existing media files from local filesystem storage to
MinIO/S3 storage, updating database records with new URLs.

Usage:
    # Dry run (preview only)
    python -m src.migrate_storage --dry-run

    # Migrate all files
    python -m src.migrate_storage

    # Migrate and delete local files after successful upload
    python -m src.migrate_storage --delete-local

    # Resume from last interrupted migration
    python -m src.migrate_storage --resume

    # Migrate specific entity type
    python -m src.migrate_storage --entity-type community
"""

import argparse
import logging
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
from sqlalchemy.orm import Session

from config.db import SessionLocal
from model.media import Media, MediaType
from src.storage import LocalFileStorage, S3Storage, get_storage_backend
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('storage_migration.log')
    ]
)
logger = logging.getLogger(__name__)


class StorageMigration:
    """Handles migration of media files from local to S3/MinIO storage"""

    def __init__(self, dry_run: bool = True, delete_local: bool = False):
        self.dry_run = dry_run
        self.delete_local = delete_local
        self.resume_file = "migration_progress.json"

        # Initialize storage backends
        self.local_storage = LocalFileStorage(
            base_dir=os.getenv("UPLOAD_DIR", "uploads"),
            base_url=os.getenv("BASE_URL", "http://localhost:8000")
        )

        self.s3_storage = S3Storage(
            bucket_name=os.getenv("S3_BUCKET_NAME", "artitec-media"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region=os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            public_base_url=os.getenv("S3_PUBLIC_BASE_URL")
        )

        self.stats = {
            'total_records': 0,
            'already_migrated': 0,
            'successfully_migrated': 0,
            'failed': 0,
            'skipped': 0,
            'local_files_deleted': 0
        }

        self.failed_records: List[Dict] = []
        self.migrated_ids: List[int] = []

    def load_progress(self) -> List[int]:
        """Load previously migrated IDs from resume file"""
        if os.path.exists(self.resume_file):
            try:
                with open(self.resume_file, 'r') as f:
                    data = json.load(f)
                    return data.get('migrated_ids', [])
            except Exception as e:
                logger.error(f"Failed to load resume file: {e}")
        return []

    def save_progress(self):
        """Save migration progress for resume capability"""
        try:
            with open(self.resume_file, 'w') as f:
                json.dump({
                    'migrated_ids': self.migrated_ids,
                    'timestamp': str(datetime.now()),
                    'stats': self.stats
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    def is_local_url(self, url: str) -> bool:
        """Check if URL points to local storage"""
        if not url:
            return False
        return ('localhost' in url or
                '127.0.0.1' in url or
                url.startswith('/uploads/') or
                url.startswith('uploads/'))

    def extract_storage_path(self, url: str) -> str:
        """Extract storage path from URL"""
        if url.startswith('http://') or url.startswith('https://'):
            # Extract path after /uploads/
            if '/uploads/' in url:
                return url.split('/uploads/')[-1]
        elif url.startswith('/uploads/'):
            return url[len('/uploads/'):]
        elif url.startswith('uploads/'):
            return url[len('uploads/'):]
        return url

    def migrate_file(self, local_path: str, media: Media) -> Tuple[bool, str, str]:
        """
        Migrate a single file from local to S3/MinIO.
        Returns (success, storage_path, access_url)
        """
        try:
            # Check if file exists locally
            file_path = self.local_storage.base_dir / local_path
            if not file_path.exists():
                logger.warning(f"Local file not found: {local_path}")
                return False, "", ""

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Create in-memory file object
            from io import BytesIO
            file_obj = BytesIO(file_content)

            # Get profile_id and entity_field for organized storage
            profile_id = None
            if hasattr(media, 'profile_id'):
                profile_id = media.profile_id

            # Extract entity field from storage path if possible
            entity_field = media.entity_field if hasattr(media, 'entity_field') else None

            # Upload to S3/MinIO (using async wrapper)
            import asyncio
            storage_path, access_url = asyncio.run(
                self.s3_storage.save(
                    file_data=file_obj,
                    filename=media.original_filename or Path(local_path).name,
                    content_type=media.content_type or 'application/octet-stream',
                    profile_id=profile_id,
                    entity_field=entity_field
                )
            )

            logger.info(f"✓ Migrated: {local_path} -> {storage_path}")
            return True, storage_path, access_url

        except Exception as e:
            logger.error(f"Failed to migrate {local_path}: {e}")
            return False, "", ""

    def update_media_record(
        self,
        db: Session,
        media: Media,
        storage_path: str,
        access_url: str
    ) -> bool:
        """Update media record with new S3/MinIO URLs"""
        try:
            # Update storage path and URL
            media.storage_path = storage_path
            media.original_url = access_url

            # Update variant URLs (they follow the same pattern)
            base_url = self.s3_storage.public_base_url or f"{self.s3_storage.endpoint_url}/{self.s3_storage.bucket_name}"

            # Generate variant paths based on storage path
            base_path = storage_path.rsplit('.', 1)[0] if '.' in storage_path else storage_path
            ext = storage_path.rsplit('.', 1)[1] if '.' in storage_path else 'jpg'

            media.thumbnail_url = f"{base_url}/{base_path}_thumb.{ext}"
            media.medium_url = f"{base_url}/{base_path}_medium.{ext}"
            media.large_url = f"{base_url}/{base_path}_large.{ext}"

            if not self.dry_run:
                db.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to update database for media {media.id}: {e}")
            if not self.dry_run:
                db.rollback()
            return False

    def delete_local_file(self, local_path: str) -> bool:
        """Delete local file after successful migration"""
        try:
            file_path = self.local_storage.base_dir / local_path
            if file_path.exists():
                file_path.unlink()
                self.stats['local_files_deleted'] += 1
                logger.info(f"🗑️  Deleted local file: {local_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete local file {local_path}: {e}")
        return False

    def migrate_media_record(self, db: Session, media: Media, already_migrated: List[int]) -> bool:
        """Migrate a single media record"""
        self.stats['total_records'] += 1

        # Skip if already migrated
        if media.id in already_migrated:
            self.stats['already_migrated'] += 1
            logger.debug(f"Skipping already migrated: {media.id}")
            return True

        # Skip embedded videos (no files to migrate)
        if media.media_type == MediaType.VIDEO and media.content_type == "video/embed":
            self.stats['skipped'] += 1
            logger.debug(f"Skipping embedded video: {media.id}")
            return True

        # Check if already on S3/MinIO
        if not self.is_local_url(media.original_url):
            self.stats['already_migrated'] += 1
            logger.debug(f"Already on S3/MinIO: {media.id}")
            self.migrated_ids.append(media.id)
            return True

        # Extract local path
        local_path = self.extract_storage_path(media.original_url)

        logger.info(f"Migrating media ID {media.id}: {local_path}")

        if self.dry_run:
            logger.info(f"DRY RUN: Would migrate {local_path}")
            self.stats['successfully_migrated'] += 1
            return True

        # Migrate file
        success, storage_path, access_url = self.migrate_file(local_path, media)

        if not success:
            self.stats['failed'] += 1
            self.failed_records.append({
                'id': media.id,
                'local_path': local_path,
                'error': 'Migration failed'
            })
            return False

        # Update database
        if self.update_media_record(db, media, storage_path, access_url):
            self.stats['successfully_migrated'] += 1
            self.migrated_ids.append(media.id)

            # Delete local file if requested
            if self.delete_local and not self.dry_run:
                self.delete_local_file(local_path)

            # Save progress periodically
            if len(self.migrated_ids) % 10 == 0:
                self.save_progress()

            return True
        else:
            self.stats['failed'] += 1
            self.failed_records.append({
                'id': media.id,
                'local_path': local_path,
                'error': 'Database update failed'
            })
            return False

    def run(self, entity_type: str = None, resume: bool = False) -> Dict:
        """Execute the migration process"""
        start_time = datetime.now()

        logger.info("="*80)
        logger.info(f"Storage Migration Started - {'DRY RUN' if self.dry_run else 'LIVE MODE'}")
        logger.info(f"Timestamp: {start_time}")
        logger.info(f"Delete local files: {self.delete_local}")
        logger.info("="*80)

        # Load progress if resuming
        already_migrated = []
        if resume:
            already_migrated = self.load_progress()
            logger.info(f"Resuming from previous run - {len(already_migrated)} already migrated")

        db = SessionLocal()
        try:
            # Build query
            query = db.query(Media)
            if entity_type:
                query = query.filter(Media.entity_type == entity_type)

            # Get all media records
            media_records = query.all()
            logger.info(f"Found {len(media_records)} media records to process")

            # Migrate each record
            for media in media_records:
                self.migrate_media_record(db, media, already_migrated)

            # Final progress save
            self.save_progress()

            # Print summary
            self.print_summary(start_time)

            return self.stats

        except KeyboardInterrupt:
            logger.warning("\n⚠️  Migration interrupted by user")
            self.save_progress()
            logger.info(f"Progress saved. Run with --resume to continue.")
            raise

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            self.save_progress()
            raise

        finally:
            db.close()

    def print_summary(self, start_time: datetime):
        """Print migration summary"""
        duration = (datetime.now() - start_time).total_seconds()

        logger.info("="*80)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Mode: {'DRY RUN (no changes made)' if self.dry_run else 'LIVE MODE'}")
        logger.info(f"Total records processed: {self.stats['total_records']}")
        logger.info(f"Already migrated/on S3: {self.stats['already_migrated']}")
        logger.info(f"Successfully migrated: {self.stats['successfully_migrated']}")
        logger.info(f"Skipped (embedded videos): {self.stats['skipped']}")
        logger.info(f"Failed: {self.stats['failed']}")

        if self.delete_local and not self.dry_run:
            logger.info(f"Local files deleted: {self.stats['local_files_deleted']}")

        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("="*80)

        if self.failed_records:
            logger.info("")
            logger.info("FAILED RECORDS:")
            for record in self.failed_records:
                logger.info(f"  • ID {record['id']}: {record['local_path']} - {record['error']}")

        if self.dry_run and self.stats['successfully_migrated'] > 0:
            logger.info("")
            logger.info("💡 To actually migrate files, run without --dry-run flag")
            logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Migrate media files from local storage to MinIO/S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be migrated (safe)
  python -m src.migrate_storage --dry-run

  # Migrate all files
  python -m src.migrate_storage

  # Migrate and delete local files after success
  python -m src.migrate_storage --delete-local

  # Resume interrupted migration
  python -m src.migrate_storage --resume

  # Migrate only community media
  python -m src.migrate_storage --entity-type community

Note: Make sure S3_ENDPOINT_URL and credentials are set in .env before running!
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode - show what would be migrated without actually migrating'
    )

    parser.add_argument(
        '--delete-local',
        action='store_true',
        help='Delete local files after successful migration to S3/MinIO'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previously interrupted migration'
    )

    parser.add_argument(
        '--entity-type',
        type=str,
        choices=['community', 'building'],
        help='Limit migration to specific entity type'
    )

    args = parser.parse_args()

    # Verify S3 configuration
    if not os.getenv("S3_ENDPOINT_URL"):
        logger.error("S3_ENDPOINT_URL not configured in .env file")
        logger.error("Please configure MinIO/S3 settings before running migration")
        sys.exit(1)

    # Create migration instance
    migration = StorageMigration(
        dry_run=args.dry_run,
        delete_local=args.delete_local
    )

    # Run migration
    try:
        stats = migration.run(
            entity_type=args.entity_type,
            resume=args.resume
        )

        # Exit with appropriate code
        if stats['failed'] > 0:
            logger.warning(f"Migration completed with {stats['failed']} failures")
            sys.exit(1)
        else:
            logger.info("Migration completed successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("Migration interrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
