"""
Fix swapped storage_path and URL fields in media table.

This script fixes media records where storage_path contains URLs
and URL fields contain paths due to a bug in media_scraper.py.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from config.db import SessionLocal
from model.media import Media, MediaType
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_storage_path_from_url(url: str) -> str:
    """
    Extract storage path from S3/MinIO URL.

    Examples:
        http://100.94.199.71:9000/artitec-media/CMY-123/gallery/image.jpg
        -> CMY-123/gallery/image.jpg

        http://127.0.0.1:8000/uploads/CMY-123/gallery/image.jpg
        -> CMY-123/gallery/image.jpg
    """
    if not url:
        return url

    # For S3/MinIO URLs: extract path after bucket name
    if '/artitec-media/' in url:
        return url.split('/artitec-media/')[-1]

    # For local URLs: extract path after /uploads/
    if '/uploads/' in url:
        return url.split('/uploads/')[-1]

    # If no pattern matches, return as-is
    return url


def is_url(value: str) -> bool:
    """Check if a value looks like a URL"""
    if not value:
        return False
    return value.startswith(('http://', 'https://'))


def fix_media_record(db: Session, media: Media, dry_run: bool = True) -> bool:
    """
    Fix a single media record by swapping storage_path and URL fields if needed.

    Returns True if record was fixed, False if no fix needed.
    """
    fixed = False

    # Skip embedded videos - they don't have files to fix
    if media.media_type == MediaType.VIDEO and media.content_type == "video/embed":
        return False

    # Check if storage_path contains a URL (it should only contain the path)
    if is_url(media.storage_path):
        logger.info(f"Fixing media ID {media.id} ({media.public_id})")
        logger.info(f"  Before: storage_path = {media.storage_path}")
        logger.info(f"          original_url = {media.original_url}")

        # Extract actual storage path from the URL
        actual_storage_path = extract_storage_path_from_url(media.storage_path)
        actual_url = media.storage_path  # The current storage_path IS the URL

        if not dry_run:
            media.storage_path = actual_storage_path
            media.original_url = actual_url

        logger.info(f"  After:  storage_path = {actual_storage_path}")
        logger.info(f"          original_url = {actual_url}")
        fixed = True

    # Also check variant URLs if they might be swapped
    # (thumbnail_url, medium_url, large_url should be URLs, not paths)
    if media.thumbnail_url and not is_url(media.thumbnail_url):
        logger.warning(f"  Thumbnail URL looks like a path: {media.thumbnail_url}")
        # We can't easily reconstruct the URL, so we'll leave it

    return fixed


def main(dry_run: bool = True):
    """Fix all media records with swapped fields"""

    logger.info("=" * 80)
    logger.info(f"Storage Path Fix - {'DRY RUN (preview only)' if dry_run else 'LIVE MODE'}")
    logger.info("=" * 80)

    db = SessionLocal()
    try:
        # Get all media records
        all_media = db.query(Media).all()
        logger.info(f"Found {len(all_media)} total media records")

        fixed_count = 0
        skipped_count = 0

        for media in all_media:
            if fix_media_record(db, media, dry_run=dry_run):
                fixed_count += 1
            else:
                skipped_count += 1

        if not dry_run:
            db.commit()
            logger.info("✅ Changes committed to database")
        else:
            logger.info("ℹ️  DRY RUN - No changes were made")

        logger.info("=" * 80)
        logger.info(f"SUMMARY:")
        logger.info(f"  Total records: {len(all_media)}")
        logger.info(f"  Fixed: {fixed_count}")
        logger.info(f"  Skipped (already correct): {skipped_count}")
        logger.info("=" * 80)

        if dry_run and fixed_count > 0:
            logger.info("")
            logger.info("💡 To apply these fixes, run with --apply flag:")
            logger.info("   python scripts/fix_storage_paths.py --apply")

    except Exception as e:
        logger.error(f"Error fixing storage paths: {e}", exc_info=True)
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fix swapped storage_path and URL fields')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    args = parser.parse_args()

    main(dry_run=not args.apply)
