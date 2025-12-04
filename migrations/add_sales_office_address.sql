-- Migration: Add sales_office_address field to builder_profiles table
-- Date: 2025-11-29
-- Description: Adds sales_office_address column to distinguish between headquarters and sales office locations

ALTER TABLE builder_profiles
ADD COLUMN sales_office_address VARCHAR(255) NULL COMMENT 'Sales office address if different from headquarters';
