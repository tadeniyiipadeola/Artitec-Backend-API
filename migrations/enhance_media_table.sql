-- Migration: Enhance Media Table
-- Description: Add new fields for enhanced media management
-- Date: 2024-11-20
-- Author: Artitec Backend Development

-- Add storage configuration columns
ALTER TABLE media
ADD COLUMN IF NOT EXISTS storage_type ENUM('local', 's3') NOT NULL DEFAULT 'local'
    COMMENT 'Storage backend: local or s3' AFTER image_hash;

ALTER TABLE media
ADD COLUMN IF NOT EXISTS bucket_name VARCHAR(100) NULL
    COMMENT 'S3/MinIO bucket name if using S3 storage' AFTER storage_type;

-- Add metadata and tagging columns
ALTER TABLE media
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT FALSE
    COMMENT 'Primary/featured media for entity' AFTER sort_order;

ALTER TABLE media
ADD COLUMN IF NOT EXISTS tags JSON NULL
    COMMENT 'Searchable tags as JSON array' AFTER source_url;

ALTER TABLE media
ADD COLUMN IF NOT EXISTS metadata JSON NULL
    COMMENT 'EXIF data, processing info, etc. as JSON' AFTER tags;

-- Add moderation column
ALTER TABLE media
ADD COLUMN IF NOT EXISTS moderation_status ENUM('pending', 'approved', 'rejected', 'flagged') NOT NULL DEFAULT 'approved'
    COMMENT 'Moderation status for content review' AFTER is_approved;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_media_is_primary ON media(is_primary);
CREATE INDEX IF NOT EXISTS idx_media_moderation_status ON media(moderation_status);
CREATE INDEX IF NOT EXISTS idx_media_storage_type ON media(storage_type);

-- Update existing records to have default values
UPDATE media SET storage_type = 'local' WHERE storage_type IS NULL;
UPDATE media SET is_primary = FALSE WHERE is_primary IS NULL;
UPDATE media SET moderation_status = 'approved' WHERE moderation_status IS NULL;

-- Verify migration
SELECT 'Migration completed successfully' AS status;

-- Display table structure
DESCRIBE media;

-- Count records
SELECT COUNT(*) AS total_media_records FROM media;
