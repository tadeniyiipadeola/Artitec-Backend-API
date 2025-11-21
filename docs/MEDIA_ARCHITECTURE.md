# Media Management System - Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Applications                         │
│          (Web, Mobile, API Consumers)                               │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                           │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Entity-Specific Upload Routes                    │  │
│  │   /users/{id}/avatar, /communities/{id}/photos, etc.         │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                        │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │              Permission Validation Layer                      │  │
│  │   - Check user ownership                                      │  │
│  │   - Verify entity access                                      │  │
│  │   - Admin override                                            │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                        │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │              Media Processing Layer                           │  │
│  │                                                                │  │
│  │   ┌──────────────┐  ┌─────────────┐  ┌──────────────┐       │  │
│  │   │   Validate   │  │   Process   │  │   Extract    │       │  │
│  │   │   File       │─▶│   Image     │─▶│   Metadata   │       │  │
│  │   └──────────────┘  └─────────────┘  └──────────────┘       │  │
│  │                                                                │  │
│  │   ┌──────────────┐  ┌─────────────┐  ┌──────────────┐       │  │
│  │   │  Generate    │  │  Calculate  │  │  Organize    │       │  │
│  │   │  Thumbnails  │─▶│  Hash       │─▶│  Storage     │       │  │
│  │   └──────────────┘  └─────────────┘  └──────────────┘       │  │
│  │                                                                │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                        │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │              Storage Abstraction Layer                        │  │
│  │   - Local filesystem (development)                            │  │
│  │   - MinIO/S3 (production)                                     │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                        │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
                 ▼            ▼            ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │  Local   │  │  MinIO   │  │   AWS    │
         │  Storage │  │ Storage  │  │    S3    │
         └──────────┘  └──────────┘  └──────────┘
                              │
                 ┌────────────┼────────────┐
                 │                         │
                 ▼                         ▼
         ┌──────────────┐         ┌──────────────┐
         │   Database   │         │     CDN      │
         │   (MySQL)    │         │  (Optional)  │
         │              │         │              │
         │  Media       │         │  Cached      │
         │  Metadata    │         │  Files       │
         └──────────────┘         └──────────────┘
```

## Component Interaction Flow

### 1. Upload Flow

```
Client Request
     │
     ▼
[Entity Route] ────▶ Validate Permissions
     │
     ▼
[Media Processor] ──┬──▶ Validate File (type, size, dimensions)
                    │
                    ├──▶ Process Image
                    │    ├── Extract EXIF
                    │    ├── Calculate Hash
                    │    ├── Fix Orientation
                    │    ├── Generate Thumbnail (150x150)
                    │    ├── Generate Small (400x400)
                    │    ├── Generate Medium (800x800)
                    │    └── Generate Large (1600x1600)
                    │
                    └──▶ Generate Storage Path
                         ({entity_type}/{media_type}/{entity_id}/{YYYY-MM}/{filename})
     │
     ▼
[Storage Service] ───┬──▶ Upload Original
                     ├──▶ Upload Thumbnail
                     ├──▶ Upload Medium
                     └──▶ Upload Large
     │
     ▼
[Database] ──────────▶ Create Media Record
     │                  - URLs
     │                  - Metadata
     │                  - Hash
     │                  - Dimensions
     │
     ▼
Return MediaOut Response
```

### 2. Retrieval Flow

```
Client Request
     │
     ▼
[Management Route] ──▶ Query Database
     │                 - Filter by entity
     │                 - Filter by field
     │                 - Order by sort_order
     │
     ▼
[Validate Files] ────▶ Check Storage Exists
     │                 (Filter orphaned records)
     │
     ▼
[Build URLs] ────────▶ Convert to Full URLs
     │                 - Use S3_PUBLIC_BASE_URL for S3
     │                 - Use BASE_URL for local
     │
     ▼
Return MediaListOut Response
```

## Data Flow Diagram

```
┌─────────────┐
│   Upload    │
│   Request   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  multipart/form  │
│      data        │
│  - file          │
│  - metadata      │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────┐
│   File Validation           │
│   ✓ Type check              │
│   ✓ Size check              │
│   ✓ Dimension check         │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Image Processing          │
│   • Read file               │
│   • Extract EXIF            │
│   • Calculate hash          │
│   • Fix orientation         │
│   • Generate variants       │
└────────┬────────────────────┘
         │
         ├─────────┬─────────┬─────────┬─────────┐
         │         │         │         │         │
         ▼         ▼         ▼         ▼         ▼
    Original  Thumbnail  Small    Medium   Large
    (Full)    (150x150)  (400x)   (800x)   (1600x)
         │         │         │         │         │
         └─────────┴─────────┴─────────┴─────────┘
                            │
                            ▼
                 ┌──────────────────┐
                 │  Storage Upload  │
                 │  (MinIO/S3)      │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Generate URLs   │
                 │  - original_url  │
                 │  - thumbnail_url │
                 │  - medium_url    │
                 │  - large_url     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Database Insert │
                 │  Media Record    │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Return Response │
                 │  MediaOut        │
                 └──────────────────┘
```

## Storage Structure

```
artitec-media (S3 Bucket)
│
├── users/
│   ├── avatars/
│   │   ├── USR-123/
│   │   │   └── 2024-11/
│   │   │       ├── avatar-20241120153045-a1b2c3.jpg
│   │   │       ├── avatar-20241120153045-a1b2c3_thumb.jpg
│   │   │       └── avatar-20241120153045-a1b2c3_medium.jpg
│   │   └── USR-456/
│   │       └── 2024-11/
│   │           └── ...
│   └── covers/
│       └── USR-123/
│           └── 2024-11/
│               └── cover-20241120153045-def456.jpg
│
├── communities/
│   └── photos/
│       ├── CMY-789/
│       │   └── 2024-11/
│       │       ├── photo-20241120153045-ghi789.jpg
│       │       ├── photo-20241120153045-ghi789_thumb.jpg
│       │       ├── photo-20241120153045-ghi789_medium.jpg
│       │       └── photo-20241120153045-ghi789_large.jpg
│       └── CMY-101/
│           └── 2024-11/
│               └── ...
│
├── properties/
│   └── photos/
│       └── PROP-112/
│           └── 2024-11/
│               └── ...
│
├── builders/
│   ├── photos/
│   │   └── BLD-131/
│   │       └── 2024-11/
│   │           └── gallery-20241120153045-jkl012.jpg
│   └── avatars/
│       └── BLD-131/
│           └── 2024-11/
│               └── avatar-20241120153045-mno345.jpg
│
└── posts/
    └── photos/
        └── 2024-11/
            └── ...
```

## Database Schema

```sql
Table: media
┌──────────────────────┬──────────────────┬─────────────────────────┐
│ Column               │ Type             │ Description             │
├──────────────────────┼──────────────────┼─────────────────────────┤
│ id                   │ INTEGER          │ Primary key             │
│ public_id            │ VARCHAR(30)      │ Public-facing ID        │
│ filename             │ VARCHAR(255)     │ Generated filename      │
│ original_filename    │ VARCHAR(255)     │ Original filename       │
│ media_type           │ ENUM             │ IMAGE or VIDEO          │
│ content_type         │ VARCHAR(100)     │ MIME type               │
│ file_size            │ BIGINT           │ Size in bytes           │
│ width                │ INTEGER          │ Image width             │
│ height               │ INTEGER          │ Image height            │
│ duration             │ INTEGER          │ Video duration (sec)    │
│ image_hash           │ VARCHAR(64)      │ Perceptual hash         │
│ storage_type         │ ENUM             │ local or s3             │
│ bucket_name          │ VARCHAR(100)     │ S3 bucket name          │
│ storage_path         │ TEXT             │ Storage path/key        │
│ original_url         │ TEXT             │ Original file URL       │
│ thumbnail_url        │ TEXT             │ Thumbnail URL           │
│ medium_url           │ TEXT             │ Medium size URL         │
│ large_url            │ TEXT             │ Large size URL          │
│ video_processed_url  │ TEXT             │ Processed video URL     │
│ entity_type          │ VARCHAR(50)      │ Entity type             │
│ entity_id            │ INTEGER          │ Entity ID               │
│ entity_field         │ VARCHAR(50)      │ Entity field            │
│ alt_text             │ VARCHAR(500)     │ Accessibility text      │
│ caption              │ TEXT             │ Caption                 │
│ sort_order           │ INTEGER          │ Order in gallery        │
│ is_primary           │ BOOLEAN          │ Primary/featured        │
│ source_url           │ TEXT             │ Source URL if scraped   │
│ tags                 │ JSON             │ Searchable tags         │
│ metadata             │ JSON             │ EXIF and other metadata │
│ uploaded_by          │ VARCHAR(30)      │ Uploader user ID        │
│ is_public            │ BOOLEAN          │ Public accessibility    │
│ is_approved          │ BOOLEAN          │ Approval status         │
│ moderation_status    │ ENUM             │ Moderation status       │
│ created_at           │ DATETIME         │ Creation timestamp      │
│ updated_at           │ DATETIME         │ Update timestamp        │
└──────────────────────┴──────────────────┴─────────────────────────┘

Indexes:
- idx_media_entity (entity_type, entity_id)
- idx_media_uploaded_by (uploaded_by)
- idx_media_created_at (created_at)
- idx_media_public_id (public_id)
- idx_media_is_primary (is_primary)
- idx_media_moderation_status (moderation_status)
- idx_media_storage_type (storage_type)
```

## Module Dependencies

```
routes/media/entities.py
    │
    ├── model/media.py
    │   └── MediaType, StorageType, ModerationStatus
    │
    ├── schema/media.py
    │   └── MediaOut, MediaUploadResponse
    │
    ├── src/media_processor.py
    │   ├── MediaValidator
    │   ├── ImageProcessorEnhanced
    │   ├── PathGenerator
    │   └── DuplicateDetector
    │
    ├── src/storage.py
    │   └── get_storage_backend()
    │
    ├── config/media_config.py
    │   └── MediaConfig
    │
    └── config/security.py
        └── get_current_user()
```

## API Endpoint Hierarchy

```
/v1/media/
│
├── /upload                      [POST]   General upload
│
├── /users/
│   ├── /{user_id}/avatar       [POST]   Upload user avatar
│   └── /{user_id}/cover        [POST]   Upload user cover
│
├── /properties/
│   └── /{property_id}/photos   [POST]   Upload property photos
│
├── /builders/
│   ├── /{builder_id}/portfolio [POST]   Upload portfolio
│   └── /{builder_id}/logo      [POST]   Upload logo
│
├── /communities/
│   ├── /{community_id}/photos  [POST]   Upload community photos
│   └── /{community_id}/amenities/
│       └── /{amenity_id}/photos [POST]  Upload amenity photos
│
├── /sales-reps/
│   └── /{rep_id}/avatar        [POST]   Upload sales rep avatar
│
├── /posts/
│   └── /{post_id}/media        [POST]   Upload post media
│
├── /batch/
│   ├── /upload                 [POST]   Batch upload
│   ├── /delete                 [POST]   Batch delete
│   └── /approve                [POST]   Batch approve
│
├── /entity/{type}/{id}         [GET]    List entity media
│
├── /{media_id}                 [GET]    Get single media
│   └── [DELETE] Delete media
│
├── /public/{public_id}         [GET]    Get by public ID
│
├── /analytics/storage          [GET]    Storage analytics
│
└── /health/storage-sync        [GET]    Health check
```

## Security & Permission Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Permission Hierarchy                      │
└─────────────────────────────────────────────────────────────┘

User Upload (Avatar/Cover)
    ├── Owner: ✓ Can upload
    └── Others: ✗ Cannot upload

Community Photos
    ├── Community Admin: ✓ Can upload
    ├── Community Members: ✗ Cannot upload
    └── Other Users: ✗ Cannot upload

Builder Portfolio/Logo
    ├── Builder Owner: ✓ Can upload
    └── Others: ✗ Cannot upload

Property Photos
    ├── Property Builder: ✓ Can upload
    ├── Authorized Users: ✓ Can upload (if granted)
    └── Others: ✗ Cannot upload

Post Media
    ├── Post Owner: ✓ Can upload
    └── Others: ✗ Cannot upload

Admin Users
    └── ALL: ✓ Can upload anywhere
```

## Performance Considerations

```
┌────────────────────────────────────────────────────────────┐
│                    Processing Time                          │
├────────────────────────────────────────────────────────────┤
│ Image Upload (single)         │  ~2-5 seconds             │
│ Image Processing (variants)   │  ~1-3 seconds             │
│ Storage Upload (MinIO)        │  ~0.5-1 second            │
│ Database Insert               │  ~0.1 second              │
│ Total (per image)             │  ~3-9 seconds             │
├────────────────────────────────────────────────────────────┤
│ Batch Upload (10 images)      │  ~30-90 seconds           │
│ Video Upload (100MB)          │  ~10-30 seconds           │
└────────────────────────────────────────────────────────────┘

Optimization Strategies:
1. Async processing for large batches
2. Background task queue (Celery/Redis)
3. CDN for serving processed images
4. Image optimization (WebP conversion)
5. Lazy thumbnail generation
```

## Error Handling

```
Upload Flow Error Handling:

File Validation Error
    └── Return 400 Bad Request
        └── Invalid file type/size

Permission Denied
    └── Return 403 Forbidden
        └── Not authorized for entity

Entity Not Found
    └── Return 404 Not Found
        └── Entity doesn't exist

Processing Error
    └── Return 500 Internal Server Error
        └── Log error, rollback DB

Storage Error
    └── Return 500 Internal Server Error
        └── Retry upload, fallback to local
```

This architecture provides a robust, scalable, and maintainable media management system for the Artitec platform.
