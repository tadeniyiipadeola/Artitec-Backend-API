# Artitec Media Management System

## Overview

A comprehensive media management system for the Artitec platform that handles file uploads, processing, storage, and management for images and videos across all entity types.

## Features

- **Multi-Entity Support**: Upload media for users, communities, properties, builders, sales reps, posts, and amenities
- **Image Processing**: Automatic thumbnail generation, resizing, and optimization
- **Duplicate Detection**: Perceptual hashing to identify duplicate images
- **EXIF Data Extraction**: Automatic extraction of camera metadata
- **Storage Flexibility**: Support for both local filesystem and MinIO/S3 storage
- **Entity-Specific Routes**: Dedicated endpoints for different upload types
- **Batch Uploads**: Upload multiple files in a single request
- **Content Moderation**: Built-in moderation workflow
- **Organized Storage**: Hierarchical path structure for easy management

## Architecture

### Components

1. **Media Model** (`model/media.py`)
   - Enhanced with storage configuration, tags, metadata, and moderation status
   - Supports polymorphic relationships with any entity

2. **Media Processor** (`src/media_processor.py`)
   - File validation
   - Image processing (resizing, thumbnails)
   - EXIF data extraction
   - Perceptual hashing for duplicate detection
   - Path generation

3. **Storage Service** (`src/storage_service.py`)
   - MinIO/S3 client wrapper
   - Upload, download, delete operations
   - Presigned URL generation
   - Bucket management

4. **Entity Routes** (`routes/media/entities.py`)
   - Dedicated upload endpoints for each entity type
   - Permission validation
   - Automatic processing and storage

5. **Configuration** (`config/media_config.py`)
   - Centralized configuration for file types, sizes, and limits
   - Thumbnail configurations
   - Storage path templates

## Installation

### Dependencies

```bash
pip install pillow imagehash boto3 minio
```

### Environment Variables

Add these to your `.env` file:

```env
# Storage Configuration
STORAGE_TYPE=s3  # or 'local' for development
UPLOAD_DIR=uploads  # for local storage

# MinIO/S3 Configuration
S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=artitec-media
AWS_REGION=us-east-1
S3_PUBLIC_BASE_URL=http://localhost:9000/artitec-media
S3_SECURE=false

# Base URL
BASE_URL=http://localhost:8000
```

## Database Migration

Run the migration to add new fields to the media table:

```bash
mysql -u your_user -p artitec < migrations/enhance_media_table.sql
```

Or using Python:

```python
python run_migration.py migrations/enhance_media_table.sql
```

## API Endpoints

### Entity-Specific Upload Routes

#### User Avatar
```http
POST /v1/media/users/{user_id}/avatar
Content-Type: multipart/form-data

file: [image file]
alt_text: "Profile photo" (optional)
```

**Response:**
```json
{
  "media": {
    "id": 123,
    "public_id": "MED-...",
    "original_url": "http://...",
    "thumbnail_url": "http://...",
    "medium_url": "http://...",
    "entity_type": "user",
    "entity_id": 1,
    "is_primary": true
  },
  "message": "Avatar uploaded successfully"
}
```

#### User Cover Photo
```http
POST /v1/media/users/{user_id}/cover
```

#### Property Photos
```http
POST /v1/media/properties/{property_id}/photos
Content-Type: multipart/form-data

file: [image file]
alt_text: "Beautiful kitchen" (optional)
caption: "Newly renovated kitchen" (optional)
is_primary: false (optional)
```

#### Builder Portfolio
```http
POST /v1/media/builders/{builder_id}/portfolio
Content-Type: multipart/form-data

file: [image file]
alt_text: "Modern home design" (optional)
caption: "One of our signature designs" (optional)
tags: "modern,luxury,custom" (optional, comma-separated)
```

#### Builder Logo
```http
POST /v1/media/builders/{builder_id}/logo
```

#### Community Photos
```http
POST /v1/media/communities/{community_id}/photos
Content-Type: multipart/form-data

file: [image file]
alt_text: "Community entrance" (optional)
caption: "Main entrance" (optional)
is_primary: false (optional)
```

#### Community Amenity Photos
```http
POST /v1/media/communities/{community_id}/amenities/{amenity_id}/photos
```

#### Sales Rep Avatar
```http
POST /v1/media/sales-reps/{rep_id}/avatar
```

#### Post Media
```http
POST /v1/media/posts/{post_id}/media
Content-Type: multipart/form-data

file: [image or video file]
alt_text: "Sunset view" (optional)
caption: "Beautiful sunset from my backyard" (optional)
```

### Batch Upload
```http
POST /v1/media/batch/upload
Content-Type: multipart/form-data

files: [multiple files]
entity_type: "property"
entity_id: 123
entity_field: "gallery"
```

**Response:**
```json
{
  "uploaded": [...],
  "uploaded_count": 5,
  "failed": [],
  "failed_count": 0,
  "message": "Successfully uploaded 5 of 5 files"
}
```

### General Upload (Legacy)
```http
POST /v1/media/upload
Content-Type: multipart/form-data

file: [file]
entity_type: "community"
entity_id: 123
entity_field: "gallery" (optional)
alt_text: "Community pool" (optional)
caption: "Resort-style pool" (optional)
sort_order: 0 (optional)
is_public: true (optional)
```

### List Media for Entity
```http
GET /v1/media/entity/{entity_type}/{entity_id}?entity_field=gallery
```

### Get Single Media
```http
GET /v1/media/{media_id}
GET /v1/media/public/{public_id}
```

### Delete Media
```http
DELETE /v1/media/{media_id}
```

### Batch Delete
```http
POST /v1/media/batch/delete
Content-Type: application/json

{
  "media_ids": [1, 2, 3, 4, 5]
}
```

### Storage Analytics
```http
GET /v1/media/analytics/storage?entity_type=community
```

## Storage Structure

Files are organized in a hierarchical structure:

```
{entity_type}s/{media_type}/{entity_id}/{YYYY-MM}/{filename}
```

### Examples:

- User avatar: `users/avatars/USR-123/2024-11/avatar-20241120153045-a1b2c3.jpg`
- Community photo: `communities/photos/CMY-456/2024-11/photo-20241120153045-def456.jpg`
- Property gallery: `properties/photos/PROP-789/2024-11/photo-20241120153045-ghi789.jpg`
- Builder portfolio: `builders/photos/BLD-012/2024-11/gallery-20241120153045-jkl012.jpg`

## Image Processing Pipeline

When an image is uploaded:

1. **Validation**: Check file type, size, and dimensions
2. **EXIF Extraction**: Extract camera metadata
3. **Perceptual Hash**: Calculate hash for duplicate detection
4. **Orientation Fix**: Auto-rotate based on EXIF orientation
5. **Generate Variants**:
   - **Thumbnail**: 150x150 (square crop)
   - **Small**: 400x400 (maintain aspect ratio)
   - **Medium**: 800x800 (maintain aspect ratio)
   - **Large**: 1600x1600 (maintain aspect ratio)
6. **Upload**: Store all variants in MinIO/S3
7. **Database Record**: Create media record with all URLs

## Permissions

- **User Avatar/Cover**: Only the user themselves
- **Community Photos**: Only community admin
- **Builder Photos/Logo**: Only builder owner
- **Sales Rep Avatar**: Only sales rep themselves
- **Property Photos**: Authorized users (builder, admin)
- **Post Media**: Post owner

## Configuration

### File Type Limits

**Images:**
- Max size: 20 MB
- Min size: 1 KB
- Formats: JPG, PNG, GIF, WebP, BMP, TIFF
- Max dimension: 8000x8000 px
- Min dimension: 50x50 px

**Videos:**
- Max size: 500 MB
- Min size: 10 KB
- Formats: MP4, MOV, AVI, MKV, WebM, M4V

**Avatars:**
- Max size: 5 MB
- Min dimension: 100x100 px
- Max dimension: 2000x2000 px

### Thumbnail Sizes

- **Thumbnail (Small)**: 150x150
- **Medium**: 400x400
- **Large**: 800x800
- **Extra Large**: 1600x1600

### JPEG Quality

- Thumbnail: 80%
- Small: 85%
- Medium: 85%
- Large: 90%

## Usage Examples

### Upload User Avatar (Python)

```python
import requests

url = "http://localhost:8000/v1/media/users/1/avatar"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
files = {"file": open("avatar.jpg", "rb")}
data = {"alt_text": "My profile photo"}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

### Upload Community Photos (cURL)

```bash
curl -X POST "http://localhost:8000/v1/media/communities/123/photos" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@photo1.jpg" \
  -F "alt_text=Community entrance" \
  -F "caption=Beautiful entrance" \
  -F "is_primary=true"
```

### Batch Upload (JavaScript)

```javascript
const formData = new FormData();
formData.append('entity_type', 'property');
formData.append('entity_id', '123');
formData.append('entity_field', 'gallery');

// Add multiple files
files.forEach(file => {
  formData.append('files', file);
});

fetch('http://localhost:8000/v1/media/batch/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})
.then(res => res.json())
.then(data => console.log(data));
```

## Duplicate Detection

The system uses perceptual hashing to detect duplicate images:

```python
from src.media_processor import DuplicateDetector

# Check if two images are duplicates
is_dup = DuplicateDetector.is_duplicate(hash1, hash2, threshold=5)

# Calculate similarity distance
distance = DuplicateDetector.calculate_hash_distance(hash1, hash2)
# distance 0 = identical
# distance 1-5 = very similar (likely duplicates)
# distance 6-10 = similar
# distance 10+ = different images
```

## MinIO Storage Service

Direct usage of MinIO service:

```python
from src.storage_service import get_minio_service

# Get service instance
minio = get_minio_service()

# Upload file
url = minio.upload_file(file_data, "path/to/file.jpg", "image/jpeg")

# Generate presigned URL (temporary access)
presigned_url = minio.generate_presigned_url("path/to/file.jpg", expiration=3600)

# Check if file exists
exists = minio.file_exists("path/to/file.jpg")

# Delete file
success = minio.delete_file("path/to/file.jpg")

# Get bucket size
stats = minio.get_bucket_size()
print(f"Total: {stats['total_size_gb']} GB, {stats['total_files']} files")
```

## Troubleshooting

### Images not displaying
- Check that `STORAGE_TYPE` is set correctly in `.env`
- Verify MinIO is running: `docker ps | grep minio`
- Check `S3_PUBLIC_BASE_URL` is accessible
- Verify bucket permissions are set to public-read

### Upload fails with "File too large"
- Check file size against limits in `config/media_config.py`
- Adjust nginx/server upload limits if needed

### Thumbnails not generated
- Ensure Pillow is installed: `pip install pillow`
- Check logs for image processing errors
- Verify image format is supported

### Video thumbnails not working
- Install ffmpeg: `brew install ffmpeg` (Mac) or `apt-get install ffmpeg` (Linux)
- Check ffmpeg is in PATH: `which ffmpeg`

## Performance Considerations

1. **Image Processing**: Done synchronously during upload
   - Consider background tasks for large images
   - Use CDN for serving processed images

2. **Storage**: MinIO provides excellent performance
   - Consider S3 for production
   - Enable CDN for static assets

3. **Thumbnails**: Generated once, cached forever
   - Set appropriate cache headers
   - Use CDN for distribution

## Security

1. **File Validation**: Strict type and size checking
2. **Permission Checks**: Entity-level access control
3. **Content Moderation**: Built-in moderation workflow
4. **EXIF Stripping**: Optional GPS data removal (privacy)
5. **Presigned URLs**: Temporary access for private files

## Future Enhancements

- [ ] Video processing and compression
- [ ] Image optimization (WebP conversion)
- [ ] AI-powered auto-tagging
- [ ] Face detection for avatars
- [ ] Watermarking support
- [ ] Background processing queue
- [ ] CDN integration
- [ ] Advanced search by tags/metadata
- [ ] Bulk operations UI

## Support

For issues or questions:
- Check logs: `tail -f logs/media.log`
- Review configuration: `config/media_config.py`
- Test endpoints: Use the provided examples above

## License

Proprietary - Artitec Platform
