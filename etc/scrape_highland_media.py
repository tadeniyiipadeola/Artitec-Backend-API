#!/usr/bin/env python3
"""
CLI script to scrape media from The Highland website

Usage:
    python scrape_highland_media.py --url https://thehighlands.com/ --community-id 1
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.media_scraper import MediaScraper


async def scrape_media(
    url: str,
    entity_type: str,
    entity_id: int,
    entity_field: str = "gallery",
    uploaded_by: str = "admin",
    max_images: int = 50,
    max_videos: int = 10
):
    """Scrape media from a URL and upload to database"""

    db = SessionLocal()

    try:
        print(f"🕷️  Scraping media from: {url}")
        print(f"📦 Entity: {entity_type} #{entity_id} ({entity_field})")
        print(f"👤 Uploaded by: {uploaded_by}")
        print(f"🎯 Limits: {max_images} images, {max_videos} videos")
        print("")

        # Initialize scraper
        scraper = MediaScraper(db=db, uploaded_by=uploaded_by)

        # Scrape the page
        media_objects, errors = await scraper.scrape_page(
            url=url,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_field=entity_field,
            max_images=max_images,
            max_videos=max_videos
        )

        # Print results
        print("")
        print("=" * 60)
        print(f"✅ SUCCESS: Scraped {len(media_objects)} media items")
        print("=" * 60)
        print("")

        if media_objects:
            print("📸 Uploaded Media:")
            for media in media_objects:
                print(f"  • {media.media_type.value}: {media.public_id}")
                print(f"    File: {media.filename}")
                print(f"    URL: {media.original_url}")
                if media.thumbnail_url:
                    print(f"    Thumbnail: {media.thumbnail_url}")
                print("")

        if errors:
            print("❌ Errors:")
            for error in errors:
                print(f"  • {error}")
            print("")

        return media_objects, errors

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return [], [str(e)]

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Scrape media from The Highland website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape The Highland homepage
  python scrape_highland_media.py --url https://thehighlands.com/ --community-id 1

  # Scrape a specific page
  python scrape_highland_media.py --url https://thehighlands.com/gallery --community-id 1 --field gallery

  # Scrape with custom limits
  python scrape_highland_media.py --url https://thehighlands.com/ --community-id 1 --max-images 100 --max-videos 20
        """
    )

    parser.add_argument(
        "--url",
        required=True,
        help="URL to scrape (e.g., https://thehighlands.com/)"
    )
    parser.add_argument(
        "--community-id",
        type=int,
        required=True,
        help="Community ID in database"
    )
    parser.add_argument(
        "--field",
        default="gallery",
        help="Entity field (default: gallery)"
    )
    parser.add_argument(
        "--entity-type",
        default="community",
        help="Entity type (default: community)"
    )
    parser.add_argument(
        "--uploaded-by",
        default="admin",
        help="User ID uploading (default: admin)"
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=50,
        help="Maximum images to scrape (default: 50)"
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=10,
        help="Maximum videos to scrape (default: 10)"
    )

    args = parser.parse_args()

    # Run the scraper
    media_objects, errors = asyncio.run(scrape_media(
        url=args.url,
        entity_type=args.entity_type,
        entity_id=args.community_id,
        entity_field=args.field,
        uploaded_by=args.uploaded_by,
        max_images=args.max_images,
        max_videos=args.max_videos
    ))

    # Exit with appropriate code
    if media_objects:
        print(f"✅ Successfully scraped {len(media_objects)} media items!")
        sys.exit(0)
    else:
        print(f"❌ Failed to scrape any media")
        sys.exit(1)


if __name__ == "__main__":
    main()
