-- Migration: Add price range fields to communities table
-- Date: 2025-12-10
-- Description: Adds price_range_min and price_range_max integer fields to the communities table
-- to track the minimum and maximum home prices in each community

-- Add price_range_min column
ALTER TABLE communities
ADD COLUMN price_range_min INT NULL COMMENT 'Minimum home price in community';

-- Add price_range_max column
ALTER TABLE communities
ADD COLUMN price_range_max INT NULL COMMENT 'Maximum home price in community';

-- Optional: Add index for price range queries if needed for filtering/sorting
-- CREATE INDEX idx_communities_price_range ON communities(price_range_min, price_range_max);
