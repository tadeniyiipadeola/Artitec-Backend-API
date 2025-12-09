#!/usr/bin/env python3
"""
Regenerate missing media variants (thumbnail, medium, large) for existing media records.

This script:
1. Finds all media records missing medium_url or large_url
2. Downloads the original image from MinIO
3. Processes it to generate missing variants
4. Uploads variants back to MinIO
5. Updates the database record

Usage:
    python regenerate_missing_media_variants.py [--dry-run] [--limit N]
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import argparse
from typing import List
import requests
from io import BytesIO

from db.database import SessionLocal
from model.media import Media
from media_processing import ImageProcessor
from storage import get_storage
from logger_config import logger


async def regenerate_variants_for_media(media: Media, storage, dry_run: bool = False) -> bool:
    """
    Regenerate missing variants for a single media record.
    Returns True if successful, False otherwise.
    """
    try:
        logger.info(f"Processing media {media.id}: {media.filename}")

        # Check what's missing
        missing = []
        if not media.thumbnail_url:
            missing.append("thumbnail")
        if not media.medium_url:
            missing.append("medium")
        if not media.large_url:
            missing.append("large")

        if not missing:
            logger.info(f"  └─ All variants exist, skipping")
            return True

        logger.info(f"  └─ Missing variants: {', '.join(missing)}")

        if dry_run:
            logger.info(f"  └─ DRY RUN: Would regenerate {', '.join(missing)}")
            return True

        # Download original image
        logger.info(f"  └─ Downloading original from: {media.original_url}")
        response = requests.get(media.original_url, timeout=30)
        response.raise_for_status()

        image_data = BytesIO(response.content)

        # Get base filename without extension
        base_filename = Path(media.filename).stem

        # Get original dimensions
        width, height = ImageProcessor.get_image_dimensions(image_data)
        logger.info(f"  └─ Original dimensions: {width}x{height}")

        # Generate missing variants
        generated_count = 0

        # Thumbnail (always generate if missing)
        if not media.thumbnail_url:
            logger.info(f"  └─ Generating thumbnail...")
            thumbnail_data = ImageProcessor.generate_thumbnail(image_data)
            if thumbnail_data:
                thumb_filename = f"{base_filename}_thumbnail.jpg"
                thumb_storage_path, thumb_url = await storage.save(
                    thumbnail_data,
                    thumb_filename,
                    media.content_type,
                    profile_id=media.entity_profile_id,
                    entity_field=media.entity_field
                )
                media.thumbnail_url = thumb_url
                generated_count += 1
                logger.info(f"     ✅ Created: {thumb_url}")

        # Medium (only if original is larger)
        if not media.medium_url and (width > ImageProcessor.MEDIUM_SIZE[0] or height > ImageProcessor.MEDIUM_SIZE[1]):
            logger.info(f"  └─ Generating medium...")
            medium_data = ImageProcessor.resize_image(
                image_data,
                ImageProcessor.MEDIUM_SIZE,
                quality=85
            )
            if medium_data:
                medium_filename = f"{base_filename}_medium.jpg"
                medium_storage_path, medium_url = await storage.save(
                    medium_data,
                    medium_filename,
                    media.content_type,
                    profile_id=media.entity_profile_id,
                    entity_field=media.entity_field
                )
                media.medium_url = medium_url
                generated_count += 1
                logger.info(f"     ✅ Created: {medium_url}")
        elif not media.medium_url:
            logger.info(f"  └─ Skipping medium (original too small: {width}x{height})")

        # Large (only if original is larger)
        if not media.large_url and (width > ImageProcessor.LARGE_SIZE[0] or height > ImageProcessor.LARGE_SIZE[1]):
            logger.info(f"  └─ Generating large...")
            large_data = ImageProcessor.resize_image(
                image_data,
                ImageProcessor.LARGE_SIZE,
                quality=90
            )
            if large_data:
                large_filename = f"{base_filename}_large.jpg"
                large_storage_path, large_url = await storage.save(
                    large_data,
                    large_filename,
                    media.content_type,
                    profile_id=media.entity_profile_id,
                    entity_field=media.entity_field
                )
                media.large_url = large_url
                generated_count += 1
                logger.info(f"     ✅ Created: {large_url}")
        elif not media.large_url:
            logger.info(f"  └─ Skipping large (original too small: {width}x{height})")

        logger.info(f"  └─ Generated {generated_count} variants")
        return generated_count > 0

    except Exception as e:
        logger.error(f"  └─ ❌ Error processing media {media.id}: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Regenerate missing media variants")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--limit", type=int, help="Limit number of media records to process")
    parser.add_argument("--entity-type", type=str, help="Only process media for this entity type (e.g., community)")
    parser.add_argument("--entity-id", type=int, help="Only process media for this entity ID")

    args = parser.parse_args()

    db = SessionLocal()
    storage = get_storage()

    try:
        # Build query
        query = db.query(Media).filter(
            Media.media_type == "IMAGE",
            # Find records missing at least one variant
            (Media.thumbnail_url == None) |
            (Media.medium_url == None) |
            (Media.large_url == None)
        )

        if args.entity_type:
            query = query.filter(Media.entity_type == args.entity_type)

        if args.entity_id:
            query = query.filter(Media.entity_id == args.entity_id)

        if args.limit:
            query = query.limit(args.limit)

        media_records: List[Media] = query.all()

        logger.info(f"{'=' * 60}")
        logger.info(f"Found {len(media_records)} media records with missing variants")
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        logger.info(f"{'=' * 60}\n")

        if not media_records:
            logger.info("No media records need processing!")
            return

        success_count = 0
        fail_count = 0

        for i, media in enumerate(media_records, 1):
            logger.info(f"\n[{i}/{len(media_records)}] Processing media ID {media.id}")

            success = await regenerate_variants_for_media(media, storage, dry_run=args.dry_run)

            if success:
                if not args.dry_run:
                    # Commit after each successful processing
                    db.commit()
                success_count += 1
            else:
                fail_count += 1

        logger.info(f"\n{'=' * 60}")
        logger.info(f"SUMMARY:")
        logger.info(f"  ✅ Success: {success_count}")
        logger.info(f"  ❌ Failed: {fail_count}")
        logger.info(f"  📊 Total: {len(media_records)}")
        logger.info(f"{'=' * 60}")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
