# Media Management System - Implementation Summary

## Overview
This document summarizes the comprehensive media management system implementation for the Artitec platform.

## Files Created/Modified

### 1. Model Enhancements
**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/model/media.py`

**Status:** MODIFIED

**Changes:**
- Added `StorageType` enum (local, s3)
- Added `ModerationStatus` enum (pending, approved, rejected, flagged)
- Added `storage_type` column
- Added `bucket_name` column
- Added `is_primary` column
- Added `tags` column (JSON)
- Added `metadata` column (JSON)
- Added `moderation_status` column

### 2. Core Utilities

#### Media Processor
**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/src/media_processor.py`

**Status:** CREATED

**Features:**
- `MediaValidator`: File validation (type, size, dimensions)
- `ImageProcessorEnhanced`: Image processing with EXIF extraction
- `PathGenerator`: Organized storage path generation
- `DuplicateDetector`: Perceptual hashing for duplicate detection
- `FileHasher`: MD5 and SHA256 hash calculation

**Key Classes:**
```python
MediaValidator.validate_file()
ImageProcessorEnhanced.process_image_complete()
PathGenerator.generate_unique_filename()
DuplicateDetector.is_duplicate()
```

#### Storage Service
**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/src/storage_service.py`

**Status:** CREATED

**Features:**
- MinIO/S3 client wrapper
- File upload/download operations
- Batch operations
- Presigned URL generation
- Bucket management
- File existence checking

**Key Methods:**
```python
MinIOStorageService.upload_file()
MinIOStorageService.delete_files()
MinIOStorageService.generate_presigned_url()
MinIOStorageService.get_bucket_size()
```

### 3. API Routes

#### Entity-Specific Routes
**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/routes/media/entities.py`

**Status:** CREATED

**Endpoints:**
- `POST /v1/media/users/{user_id}/avatar`
- `POST /v1/media/users/{user_id}/cover`
- `POST /v1/media/properties/{property_id}/photos`
- `POST /v1/media/builders/{builder_id}/portfolio`
- `POST /v1/media/builders/{builder_id}/logo`
- `POST /v1/media/communities/{community_id}/photos`
- `POST /v1/media/communities/{community_id}/amenities/{amenity_id}/photos`
- `POST /v1/media/sales-reps/{rep_id}/avatar`
- `POST /v1/media/posts/{post_id}/media`
- `POST /v1/media/batch/upload`

**Features:**
- Permission validation per entity
- Automatic image processing
- Storage path organization
- Metadata extraction

#### Routes Integration
**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/routes/media/__init__.py`

**Status:** MODIFIED

**Changes:**
- Added import for `entities` router
- Registered entity routes with main media router

### 4. Schemas

**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/schema/media.py`

**Status:** MODIFIED

**Changes:**
- Added `StorageType` enum
- Added `ModerationStatus` enum
- Enhanced `MediaOut` schema with new fields:
  - `image_hash`
  - `storage_type`
  - `bucket_name`
  - `is_primary`
  - `tags`
  - `metadata`
  - `moderation_status`
- Enhanced `MediaUpdateRequest` with:
  - `is_primary`
  - `tags`
  - `moderation_status`
- Added `BatchUploadRequest` schema

### 5. Configuration

**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/config/media_config.py`

**Status:** CREATED

**Features:**
- Centralized media configuration
- File type definitions
- Size limits configuration
- Thumbnail size configurations
- Storage path templates
- Video processing presets
- Content moderation settings
- EXIF extraction settings
- Helper methods for configuration access

**Key Constants:**
```python
ALLOWED_IMAGE_TYPES
ALLOWED_VIDEO_TYPES
MAX_IMAGE_SIZE = 20 MB
MAX_VIDEO_SIZE = 500 MB
IMAGE_SIZES = {thumbnail, small, medium, large}
```

### 6. Database Migration

**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/migrations/enhance_media_table.sql`

**Status:** CREATED

**Changes:**
```sql
ALTER TABLE media ADD COLUMN storage_type ENUM('local', 's3');
ALTER TABLE media ADD COLUMN bucket_name VARCHAR(100);
ALTER TABLE media ADD COLUMN is_primary BOOLEAN;
ALTER TABLE media ADD COLUMN tags JSON;
ALTER TABLE media ADD COLUMN metadata JSON;
ALTER TABLE media ADD COLUMN moderation_status ENUM(...);
```

**Indexes Added:**
- `idx_media_is_primary`
- `idx_media_moderation_status`
- `idx_media_storage_type`

### 7. Documentation

#### Main Documentation
**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/docs/MEDIA_MANAGEMENT_SYSTEM.md`

**Status:** CREATED

**Contents:**
- System overview
- Architecture documentation
- Installation instructions
- API endpoint reference
- Usage examples (Python, cURL, JavaScript)
- Configuration reference
- Troubleshooting guide
- Security considerations

#### Dependencies Documentation
**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/docs/MEDIA_DEPENDENCIES.txt`

**Status:** CREATED

**Required Dependencies:**
```
Pillow>=10.0.0
imagehash>=4.3.1
boto3>=1.28.0
minio>=7.1.0
```

### 8. Tests

**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/tests/test_media_system.py`

**Status:** CREATED

**Test Coverage:**
- Import verification
- Dependency checking
- Configuration validation
- Media processor functionality
- Model enum verification
- Environment variable validation

## Installation Steps

### 1. Install Dependencies
```bash
pip install pillow imagehash boto3 minio
```

### 2. Run Database Migration
```bash
mysql -u your_user -p artitec < migrations/enhance_media_table.sql
```

### 3. Configure Environment
Add to `.env`:
```env
STORAGE_TYPE=s3
S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=artitec-media
S3_PUBLIC_BASE_URL=http://localhost:9000/artitec-media
```

### 4. Verify Setup
```bash
python tests/test_media_system.py
```

## Usage Examples

### Upload User Avatar
```python
import requests

url = "http://localhost:8000/v1/media/users/1/avatar"
headers = {"Authorization": "Bearer YOUR_TOKEN"}
files = {"file": open("avatar.jpg", "rb")}
data = {"alt_text": "My profile photo"}

response = requests.post(url, headers=headers, files=files, data=data)
```

### Upload Community Photos
```bash
curl -X POST "http://localhost:8000/v1/media/communities/123/photos" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@photo.jpg" \
  -F "is_primary=true"
```

### Batch Upload
```python
files = [
    ('files', open('photo1.jpg', 'rb')),
    ('files', open('photo2.jpg', 'rb')),
]
data = {
    'entity_type': 'property',
    'entity_id': 123,
    'entity_field': 'gallery'
}

response = requests.post(
    'http://localhost:8000/v1/media/batch/upload',
    headers={'Authorization': f'Bearer {token}'},
    files=files,
    data=data
)
```

## Storage Structure

Files are organized as:
```
{entity_type}s/{media_type}/{entity_id}/{YYYY-MM}/{filename}
```

Examples:
- `users/avatars/USR-123/2024-11/avatar-20241120153045-a1b2c3.jpg`
- `communities/photos/CMY-456/2024-11/photo-20241120153045-def456.jpg`
- `builders/photos/BLD-789/2024-11/gallery-20241120153045-ghi789.jpg`

## Image Processing Pipeline

1. **Validation**: Type, size, dimension checks
2. **EXIF Extraction**: Camera metadata
3. **Perceptual Hash**: Duplicate detection
4. **Orientation Fix**: Auto-rotate
5. **Generate Variants**:
   - Thumbnail: 150x150 (square)
   - Small: 400x400
   - Medium: 800x800
   - Large: 1600x1600
6. **Upload**: All variants to storage
7. **Database**: Create media record

## Key Features

### 1. Multi-Entity Support
Dedicated endpoints for:
- Users (avatar, cover)
- Communities (photos, amenity photos)
- Properties (photos)
- Builders (portfolio, logo)
- Sales Reps (avatar)
- Posts (media)

### 2. Permission Validation
- Entity-level access control
- User ownership verification
- Admin override capability

### 3. Image Processing
- Automatic thumbnail generation
- Multiple size variants
- EXIF data extraction
- Perceptual hashing
- Orientation correction

### 4. Storage Flexibility
- Local filesystem (development)
- MinIO/S3 (production)
- Organized path structure
- Public and private access

### 5. Content Moderation
- Approval workflow
- Status tracking (pending, approved, rejected, flagged)
- Auto-approval for verified users

### 6. Duplicate Detection
- Perceptual hashing (imagehash)
- Configurable similarity threshold
- Prevents duplicate uploads

### 7. Metadata Management
- EXIF data storage (JSON)
- Custom tags (JSON array)
- Caption and alt text
- Primary media flagging

## API Summary

### Upload Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/users/{id}/avatar` | POST | User avatar |
| `/users/{id}/cover` | POST | User cover photo |
| `/properties/{id}/photos` | POST | Property photos |
| `/builders/{id}/portfolio` | POST | Builder portfolio |
| `/builders/{id}/logo` | POST | Builder logo |
| `/communities/{id}/photos` | POST | Community photos |
| `/communities/{id}/amenities/{aid}/photos` | POST | Amenity photos |
| `/sales-reps/{id}/avatar` | POST | Sales rep avatar |
| `/posts/{id}/media` | POST | Post media |
| `/batch/upload` | POST | Batch upload |

### Management Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/entity/{type}/{id}` | GET | List entity media |
| `/{id}` | GET | Get single media |
| `/public/{id}` | GET | Get by public ID |
| `/{id}` | DELETE | Delete media |
| `/batch/delete` | POST | Batch delete |
| `/analytics/storage` | GET | Storage stats |

## Security

1. **File Validation**: Strict type/size checking
2. **Permission Checks**: Entity-level authorization
3. **Content Moderation**: Approval workflow
4. **EXIF Stripping**: Optional GPS removal
5. **Presigned URLs**: Temporary access for private files

## Performance

1. **Image Processing**: Synchronous (consider async for large batches)
2. **Storage**: MinIO provides excellent performance
3. **Caching**: Generate once, cache forever
4. **CDN Ready**: Supports CDN integration

## Future Enhancements

- [ ] Background processing queue
- [ ] Video thumbnail extraction
- [ ] Video compression
- [ ] AI-powered auto-tagging
- [ ] Face detection
- [ ] Watermarking
- [ ] WebP conversion
- [ ] Advanced duplicate detection
- [ ] Bulk operations UI
- [ ] CDN integration

## Troubleshooting

### Images not displaying
- Check `STORAGE_TYPE` in `.env`
- Verify MinIO is running
- Check `S3_PUBLIC_BASE_URL`

### Upload fails
- Check file size limits
- Verify nginx upload limits
- Check storage permissions

### Thumbnails not generated
- Install Pillow: `pip install pillow`
- Check image format support

## Support

- Documentation: `/docs/MEDIA_MANAGEMENT_SYSTEM.md`
- Test suite: `python tests/test_media_system.py`
- Configuration: `config/media_config.py`

## Summary

**Total Files Created:** 7
- `src/media_processor.py` (Enhanced processor)
- `src/storage_service.py` (MinIO service)
- `routes/media/entities.py` (Entity-specific routes)
- `config/media_config.py` (Configuration)
- `migrations/enhance_media_table.sql` (Migration)
- `docs/MEDIA_MANAGEMENT_SYSTEM.md` (Documentation)
- `tests/test_media_system.py` (Test suite)

**Total Files Modified:** 3
- `model/media.py` (Enhanced model)
- `schema/media.py` (Enhanced schemas)
- `routes/media/__init__.py` (Route registration)

**Dependencies Required:**
- Pillow (image processing)
- imagehash (duplicate detection)
- boto3 (S3/MinIO client)
- minio (optional, boto3 is sufficient)

The media management system is now complete and ready for use!
