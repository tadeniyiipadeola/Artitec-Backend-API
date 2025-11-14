# Media Scraper Guide

Automatically scrape photos and videos from external websites and import them into your Artitec media system.

## 🎯 Features

- **Web Scraping**: Automatically extract images and videos from any webpage
- **Direct URL Import**: Download specific media files from direct URLs
- **Batch Processing**: Import multiple media files at once
- **Smart Detection**: Automatically detects image vs video files
- **Video Embed Support**: Handles YouTube and Vimeo embeds
- **Image Processing**: Automatic thumbnail generation and resizing
- **API & CLI**: Use via REST API or command-line interface

## 📦 Components

### Backend Files Created
```
Backend/
├── src/media_scraper.py              # Core scraper service
├── routes/media_scraper.py           # API endpoints
└── scrape_highland_media.py          # CLI script
```

### Dependencies Installed
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests
- `lxml` - Fast XML/HTML parser

## 🚀 Usage

### Method 1: CLI Script (Recommended for Initial Import)

The easiest way to scrape The Highland website:

```bash
cd "Artitec Backend Development"
source .venv/bin/activate

# Scrape The Highland homepage
python scrape_highland_media.py \
  --url https://thehighlands.com/ \
  --community-id 1 \
  --max-images 50 \
  --max-videos 10
```

**Options:**
- `--url` - URL to scrape (required)
- `--community-id` - Community ID in database (required)
- `--field` - Entity field (default: gallery)
- `--entity-type` - Entity type (default: community)
- `--uploaded-by` - User ID (default: admin)
- `--max-images` - Max images to scrape (default: 50)
- `--max-videos` - Max videos to scrape (default: 10)

**Examples:**

```bash
# Scrape The Highland gallery page
python scrape_highland_media.py \
  --url https://thehighlands.com/gallery \
  --community-id 1 \
  --field gallery

# Scrape with high limits
python scrape_highland_media.py \
  --url https://thehighlands.com/ \
  --community-id 1 \
  --max-images 100 \
  --max-videos 20
```

### Method 2: API Endpoints

Use the REST API for programmatic access:

#### Scrape a Webpage

```http
POST /v1/media/scraper/scrape-page
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://thehighlands.com/",
  "entity_type": "community",
  "entity_id": 1,
  "entity_field": "gallery",
  "max_images": 50,
  "max_videos": 10
}
```

**Response:**
```json
{
  "success": true,
  "media_count": 25,
  "media": [
    {
      "id": 1,
      "public_id": "med_abc123",
      "media_type": "image",
      "original_url": "http://localhost:8000/uploads/images/scraped_abc123.jpg",
      "thumbnail_url": "http://localhost:8000/uploads/images/scraped_abc123_thumb.jpg",
      ...
    }
  ],
  "errors": []
}
```

#### Download from Direct URL

```http
POST /v1/media/scraper/download-url
Authorization: Bearer <token>
Content-Type: application/json

{
  "media_url": "https://example.com/photo.jpg",
  "entity_type": "community",
  "entity_id": 1,
  "entity_field": "gallery",
  "caption": "Beautiful view"
}
```

#### Batch Download

```http
POST /v1/media/scraper/batch-download
Authorization: Bearer <token>
Content-Type: application/json

{
  "media_urls": [
    "https://example.com/photo1.jpg",
    "https://example.com/photo2.jpg",
    "https://example.com/video1.mp4"
  ],
  "entity_type": "community",
  "entity_id": 1,
  "entity_field": "gallery"
}
```

## 🔍 How It Works

### Web Page Scraping

The scraper analyzes HTML to find media:

**Images:**
- `<img>` tags (including `data-src`, `data-lazy-src`)
- `<picture>` and `<source>` tags
- CSS background images
- Filters out small images, icons, logos

**Videos:**
- `<video>` tags and nested `<source>` tags
- YouTube embed URLs
- Vimeo embed URLs
- Direct video file links

### Media Processing

After downloading:

**Images:**
1. Download original image
2. Generate thumbnail (150x150)
3. Generate medium size (800px)
4. Generate large size (1600px)
5. Upload all sizes to storage
6. Create database record

**Videos:**
1. Download video file (or save embed URL)
2. Extract thumbnail from first frame
3. Get metadata (duration, dimensions)
4. Upload to storage
5. Create database record

## 📝 Use Cases

### 1. Import The Highland Media

Scrape all photos and videos from The Highland's website:

```bash
# Initial import
python scrape_highland_media.py \
  --url https://thehighlands.com/ \
  --community-id 1 \
  --field gallery

# Import specific amenity photos
python scrape_highland_media.py \
  --url https://thehighlands.com/amenities \
  --community-id 1 \
  --field amenities
```

### 2. Import Builder Portfolio

Scrape a builder's portfolio website:

```bash
python scrape_highland_media.py \
  --url https://builder-website.com/portfolio \
  --entity-type builder \
  --community-id 5 \
  --field portfolio
```

### 3. Import Property Photos

Scrape photos for a specific property listing:

```bash
python scrape_highland_media.py \
  --url https://example.com/property/123 \
  --entity-type property \
  --community-id 123 \
  --field gallery
```

### 4. Scheduled Imports

Set up a cron job to periodically check for new media:

```bash
# crontab -e
# Run daily at 2 AM
0 2 * * * cd /path/to/backend && source .venv/bin/activate && python scrape_highland_media.py --url https://thehighlands.com/ --community-id 1 >> logs/scraper.log 2>&1
```

## 🎨 Advanced Usage

### Custom Scraping with Python

```python
from src.database import SessionLocal
from src.media_scraper import MediaScraper

async def custom_scrape():
    db = SessionLocal()
    scraper = MediaScraper(db=db, uploaded_by="admin")

    # Scrape a page
    media, errors = await scraper.scrape_page(
        url="https://thehighlands.com/",
        entity_type="community",
        entity_id=1,
        entity_field="gallery",
        max_images=100
    )

    print(f"Scraped {len(media)} items")

    db.close()
```

### Download Specific URLs

```python
async def download_specific_images():
    db = SessionLocal()
    scraper = MediaScraper(db=db, uploaded_by="admin")

    urls = [
        "https://example.com/hero-image.jpg",
        "https://example.com/gallery/photo1.jpg",
        "https://example.com/videos/tour.mp4"
    ]

    for url in urls:
        media = await scraper.download_from_url(
            media_url=url,
            entity_type="community",
            entity_id=1,
            entity_field="gallery"
        )
        print(f"Downloaded: {media.public_id}")

    db.close()
```

## 🛡️ Security & Best Practices

### Rate Limiting

**Be respectful:**
- Don't scrape too aggressively
- Add delays between requests if needed
- Respect `robots.txt`

```python
import time

for url in urls:
    await scraper.download_from_url(...)
    time.sleep(1)  # 1 second delay
```

### Authentication

**API endpoints require authentication:**
- All scraper endpoints require valid JWT token
- Only authenticated users can import media
- Media is attributed to the authenticated user

### Error Handling

**The scraper handles:**
- Network timeouts
- Invalid URLs
- Unsupported file types
- Processing errors

Errors are returned in the response but don't stop batch operations.

### Storage Limits

**Consider:**
- Maximum images per scrape (default: 50)
- Maximum videos per scrape (default: 10)
- File size limits (default: 50MB)
- Storage space on your NAS

## 🐛 Troubleshooting

### No Media Found

**Problem:** Scraper returns 0 media items

**Solutions:**
- Check if the website uses JavaScript to load images (scraper only processes static HTML)
- Try scraping a different page
- Use browser DevTools to inspect image URLs
- Use direct URL download instead

### Download Fails

**Problem:** "Failed to download" errors

**Solutions:**
- Check if URLs are publicly accessible
- Verify network connectivity
- Check if website blocks scrapers (User-Agent)
- Try downloading manually first

### Images Are Icons/Logos

**Problem:** Scraper downloads small icons instead of photos

**Solutions:**
- The scraper filters common icon patterns
- Adjust filtering logic in `_is_valid_image_url()`
- Use custom field to organize different types

### Database Errors

**Problem:** "Can't connect to MySQL" errors

**Solutions:**
- Ensure MariaDB is running on NAS
- Check `.env` database configuration
- Verify network connectivity to NAS
- Test connection: `mysql -h NAS_IP -u root -p`

## 📊 Monitoring

### Check Scraper Status

```bash
curl http://localhost:8000/v1/media/scraper/health
```

### View Scraped Media

```bash
# List all media for community 1
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/v1/media/entity/community/1
```

### API Documentation

Visit http://localhost:8000/docs to see interactive API documentation for all scraper endpoints.

## 🎯 Next Steps

1. **Start your MariaDB** on NAS if not running
2. **Create The Highland community** in your database (or note its ID)
3. **Run the scraper:**
   ```bash
   python scrape_highland_media.py --url https://thehighlands.com/ --community-id 1
   ```
4. **View imported media** via API or iOS app
5. **Schedule periodic imports** if needed

## 💡 Tips

- Start with small limits (`--max-images 10`) to test
- Use specific pages (e.g., `/gallery`) instead of homepage
- Check media quality after import
- Delete unwanted media via API
- Use different `entity_field` values to organize media types
- Consider downloading high-resolution versions manually for hero images

## 🆘 Need Help?

- Check logs: `tail -f logs/scraper.log`
- View API docs: http://localhost:8000/docs
- Inspect HTML: Use browser DevTools on target website
- Test URLs: Try downloading individual URLs first

---

**Happy Scraping!** 🕷️📸
