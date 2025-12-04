-- Migration: Rename address to headquarters_address in builder_profiles table
-- Date: 2025-11-29
-- Description: Renames the address column to headquarters_address for better clarity

ALTER TABLE builder_profiles
CHANGE COLUMN address headquarters_address VARCHAR(255) NULL COMMENT 'Full headquarters address';
