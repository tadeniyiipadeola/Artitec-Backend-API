-- Migration: Rename community_ids to community_id in builder_profiles table
-- Date: 2025-11-29
-- Description: Renames the misleading plural column name to singular since it only stores ONE community ID
-- NOTE: This migration is OPTIONAL - the SQLAlchemy model already maps community_id -> community_ids column

-- OPTIONAL: Rename the column to fix the misleading plural name
-- Uncomment the following line if you want to rename the actual database column:
-- ALTER TABLE builder_profiles CHANGE COLUMN community_ids community_id VARCHAR(255);

-- If you run the rename, you'll also need to update the SQLAlchemy model to remove the explicit column name mapping:
-- Change: community_id = Column('community_ids', String(255), nullable=True)
-- To:     community_id = Column(String(255), nullable=True)
