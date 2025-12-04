-- Migration: Enhance community_amenities table
-- Date: 2025-11-29
-- Description: Adds timestamp columns and index to community_amenities table for better tracking

-- Add created_at and updated_at columns if they don't exist
ALTER TABLE community_amenities
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL;

-- Add index on community_id for faster lookups
ALTER TABLE community_amenities
ADD INDEX IF NOT EXISTS idx_community_amenities_community_id (community_id);

-- Update existing rows to have proper timestamps (if any exist)
UPDATE community_amenities
SET created_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE created_at IS NULL;
