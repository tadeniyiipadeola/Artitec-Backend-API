-- Migration: Add price range fields to builder_profiles table
-- Date: 2025-11-29
-- Description: Adds price_range_min and price_range_max columns to capture the typical price range of homes built by the builder

ALTER TABLE builder_profiles
ADD COLUMN price_range_min INT NULL COMMENT 'Minimum price for homes built by this builder',
ADD COLUMN price_range_max INT NULL COMMENT 'Maximum price for homes built by this builder';
