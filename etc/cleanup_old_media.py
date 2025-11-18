#!/usr/bin/env python3
"""
Auto-cleanup script for unapproved scraped media.

Deletes media that:
- is_approved = False (not selected/approved by user)
- created_at older than 7 days

Run this script daily via cron job:
  0 2 * * * cd /path/to/project && .venv/bin/python cleanup_old_media.py
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from config.db import SessionLocal
from model.media import Media
from src.storage import get_storage_backend

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def cleanup_old_unapproved_media(dry_run: bool = False):
    """
    Delete unapproved media older than 7 days.

    Args:
        dry_run: If True, only log what would be deleted without actually deleting
    """
    db: Session = SessionLocal()
    storage = get_storage_backend()

    try:
        # Calculate cutoff date (7 days ago)
        cutoff_date = datetime.now() - timedelta(days=7)

        logger.info(f"🔍 Searching for unapproved media older than {cutoff_date}")

        # Find unapproved media older than 7 days
        old_media = db.query(Media).filter(
            Media.is_approved == False,
            Media.created_at < cutoff_date
        ).all()

        if not old_media:
            logger.info("✅ No old unapproved media found. Database is clean!")
            return

        logger.info(f"📋 Found {len(old_media)} unapproved media items to clean up")

        deleted_count = 0
        failed_count = 0
        total_size = 0

        for media in old_media:
            try:
                # Calculate age
                age_days = (datetime.now() - media.created_at).days

                logger.info(
                    f"{'[DRY RUN] Would delete' if dry_run else 'Deleting'}: "
                    f"{media.public_id} ({media.filename}) - "
                    f"{age_days} days old, Entity: {media.entity_type}/{media.entity_id}"
                )

                if not dry_run:
                    # Delete from storage
                    if media.storage_path:
                        try:
                            await storage.delete(media.storage_path)
                            logger.debug(f"  ✓ Deleted from storage: {media.storage_path}")
                        except Exception as storage_error:
                            logger.warning(f"  ⚠️ Failed to delete from storage: {storage_error}")

                    # Delete from database
                    total_size += media.file_size
                    db.delete(media)

                deleted_count += 1

            except Exception as e:
                logger.error(f"  ❌ Failed to delete {media.public_id}: {e}")
                failed_count += 1

        if not dry_run:
            db.commit()
            logger.info(f"✅ Cleanup complete!")
            logger.info(f"   Deleted: {deleted_count} items")
            logger.info(f"   Failed: {failed_count} items")
            logger.info(f"   Space freed: {total_size / 1024 / 1024:.2f} MB")
        else:
            logger.info(f"[DRY RUN] Would delete {deleted_count} items, freeing ~{total_size / 1024 / 1024:.2f} MB")

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def approve_media_batch(media_ids: list[int]):
    """
    Approve multiple media items to prevent auto-deletion.

    Args:
        media_ids: List of media IDs to approve
    """
    db: Session = SessionLocal()

    try:
        approved_count = db.query(Media).filter(
            Media.id.in_(media_ids),
            Media.is_approved == False
        ).update({"is_approved": True}, synchronize_session=False)

        db.commit()

        logger.info(f"✅ Approved {approved_count} media items")

    except Exception as e:
        logger.error(f"❌ Failed to approve media: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        logger.info("🔍 Running in DRY RUN mode (no actual deletions)")

    # Run cleanup
    asyncio.run(cleanup_old_unapproved_media(dry_run=dry_run))
