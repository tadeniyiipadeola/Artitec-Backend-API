"""
Automatic orphan cleanup script for media files.

This script scans the database for media records that don't have
corresponding files in storage and removes the orphaned database records.

Can be run manually or scheduled as a cron job.

Usage:
    # Dry run (preview only, no deletions)
    python -m src.cleanup_orphans --dry-run

    # Actually delete orphaned records
    python -m src.cleanup_orphans

    # Limit to specific entity type
    python -m src.cleanup_orphans --entity-type community

    # Process in batches
    python -m src.cleanup_orphans --batch-size 50
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import List, Tuple
from sqlalchemy.orm import Session

from config.db import SessionLocal
from model.media import Media, MediaType
from src.storage import get_storage_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('orphan_cleanup.log')
    ]
)
logger = logging.getLogger(__name__)


class OrphanCleanup:
    """Handles cleanup of orphaned media records"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.storage = get_storage_backend()
        self.stats = {
            'total_scanned': 0,
            'orphans_found': 0,
            'orphans_deleted': 0,
            'errors': 0,
            'skipped_embedded': 0
        }

    def check_media_exists(self, media: Media) -> bool:
        """
        Check if media file exists in storage.
        Returns True if file exists or is embedded video.
        """
        # Skip embedded videos (these don't have storage files)
        if media.media_type == MediaType.VIDEO and media.content_type == "video/embed":
            self.stats['skipped_embedded'] += 1
            return True

        # Check if storage path exists
        if not media.storage_path:
            logger.warning(f"Media {media.id} has no storage_path")
            return False

        # Check actual file existence
        try:
            exists = self.storage.file_exists(media.storage_path)
            if not exists:
                logger.debug(f"Orphan detected: Media ID {media.id} - {media.storage_path}")
            return exists
        except Exception as e:
            logger.error(f"Error checking media {media.id}: {e}")
            self.stats['errors'] += 1
            return True  # Don't delete on error (be conservative)

    def find_orphans(
        self,
        db: Session,
        entity_type: str = None,
        batch_size: int = 100
    ) -> List[Media]:
        """
        Scan database for orphaned media records.
        Returns list of orphaned Media objects.
        """
        logger.info("Starting orphan scan...")

        # Build query
        query = db.query(Media)
        if entity_type:
            query = query.filter(Media.entity_type == entity_type)

        # Process in batches
        orphans = []
        offset = 0

        while True:
            batch = query.offset(offset).limit(batch_size).all()
            if not batch:
                break

            for media in batch:
                self.stats['total_scanned'] += 1

                if not self.check_media_exists(media):
                    orphans.append(media)
                    self.stats['orphans_found'] += 1
                    logger.info(
                        f"Orphan found: ID={media.id}, "
                        f"type={media.media_type.value}, "
                        f"path={media.storage_path}, "
                        f"entity={media.entity_type}/{media.entity_id}"
                    )

            offset += batch_size
            logger.info(f"Scanned {self.stats['total_scanned']} records so far...")

        logger.info(f"Scan complete. Found {len(orphans)} orphaned records.")
        return orphans

    def delete_orphans(self, db: Session, orphans: List[Media]) -> int:
        """
        Delete orphaned media records from database.
        Returns count of successfully deleted records.
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would delete {len(orphans)} orphaned records")
            return 0

        deleted_count = 0
        for media in orphans:
            try:
                db.delete(media)
                db.commit()
                deleted_count += 1
                self.stats['orphans_deleted'] += 1
                logger.info(f"Deleted orphaned record: ID={media.id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to delete media {media.id}: {e}")
                self.stats['errors'] += 1

        logger.info(f"Successfully deleted {deleted_count} orphaned records")
        return deleted_count

    def run(
        self,
        entity_type: str = None,
        batch_size: int = 100
    ) -> Tuple[int, int]:
        """
        Execute the cleanup process.
        Returns (total_scanned, total_deleted).
        """
        start_time = datetime.now()
        logger.info("="*80)
        logger.info(f"Orphan Cleanup Started - {'DRY RUN' if self.dry_run else 'LIVE MODE'}")
        logger.info(f"Timestamp: {start_time}")
        logger.info("="*80)

        db = SessionLocal()
        try:
            # Find orphans
            orphans = self.find_orphans(db, entity_type, batch_size)

            # Delete orphans (or preview in dry-run mode)
            self.delete_orphans(db, orphans)

            # Print summary
            self.print_summary(start_time)

            return self.stats['total_scanned'], self.stats['orphans_deleted']

        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            raise
        finally:
            db.close()

    def print_summary(self, start_time: datetime):
        """Print summary statistics"""
        duration = (datetime.now() - start_time).total_seconds()

        logger.info("="*80)
        logger.info("CLEANUP SUMMARY")
        logger.info("="*80)
        logger.info(f"Mode: {'DRY RUN (no changes made)' if self.dry_run else 'LIVE MODE (records deleted)'}")
        logger.info(f"Total records scanned: {self.stats['total_scanned']}")
        logger.info(f"Orphans found: {self.stats['orphans_found']}")
        logger.info(f"Orphans deleted: {self.stats['orphans_deleted']}")
        logger.info(f"Embedded videos skipped: {self.stats['skipped_embedded']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("="*80)

        if self.dry_run and self.stats['orphans_found'] > 0:
            logger.info("")
            logger.info("💡 To actually delete these orphaned records, run without --dry-run flag")
            logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Clean up orphaned media database records',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be deleted (safe)
  python -m src.cleanup_orphans --dry-run

  # Actually delete orphaned records
  python -m src.cleanup_orphans

  # Clean up only community media
  python -m src.cleanup_orphans --entity-type community

  # Process in smaller batches
  python -m src.cleanup_orphans --batch-size 50

Cron job example (run daily at 2 AM):
  0 2 * * * cd /path/to/project && source .venv/bin/activate && python -m src.cleanup_orphans >> /var/log/orphan_cleanup.log 2>&1
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode - show what would be deleted without actually deleting'
    )

    parser.add_argument(
        '--entity-type',
        type=str,
        choices=['community', 'building'],
        help='Limit cleanup to specific entity type'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of records to process per batch (default: 100)'
    )

    args = parser.parse_args()

    # Create cleanup instance
    cleanup = OrphanCleanup(dry_run=args.dry_run)

    # Run cleanup
    try:
        total_scanned, total_deleted = cleanup.run(
            entity_type=args.entity_type,
            batch_size=args.batch_size
        )

        # Exit with appropriate code
        if total_deleted > 0 or (args.dry_run and cleanup.stats['orphans_found'] > 0):
            sys.exit(0)  # Success
        else:
            logger.info("No orphaned records found. Database is clean!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\nCleanup interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
