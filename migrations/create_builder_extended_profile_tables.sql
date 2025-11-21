-- Migration: Create builder extended profile tables
-- Date: 2025-11-20
-- Description: Creates tables for builder awards, home plans, and credentials
--              - builder_awards: Track awards and recognitions
--              - builder_home_plans: Manage available home plan offerings
--              - builder_credentials: Store licenses, certifications, and memberships

-- ===========================================================================
-- Table: builder_awards (skip if already exists)
-- ===========================================================================
-- Note: This table may already exist, so we only create indexes if needed


-- ===========================================================================
-- Table: builder_home_plans
-- ===========================================================================
CREATE TABLE IF NOT EXISTS builder_home_plans (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Builder this home plan belongs to (FK to builder_profiles.id - internal ID)
    builder_id INT NOT NULL,

    -- Home plan details
    name VARCHAR(255) NOT NULL,
    series VARCHAR(255) NOT NULL,
    sqft INT NOT NULL,
    beds INT NOT NULL,
    baths FLOAT NOT NULL,
    stories INT NOT NULL,
    starting_price VARCHAR(64) NOT NULL,
    description TEXT,
    image_url VARCHAR(1024),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (builder_id) REFERENCES builder_profiles(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_builder_id (builder_id),
    INDEX idx_series (series),
    INDEX idx_sqft (sqft),
    INDEX idx_price_range (starting_price)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add comment
ALTER TABLE builder_home_plans COMMENT = 'Builder home plan offerings and floor plans';


-- ===========================================================================
-- Table: builder_credentials
-- ===========================================================================
CREATE TABLE IF NOT EXISTS builder_credentials (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Builder this credential belongs to (FK to builder_profiles.id - internal ID)
    builder_id INT NOT NULL,

    -- Credential details
    name VARCHAR(255) NOT NULL,
    credential_type VARCHAR(64) NOT NULL,  -- 'license', 'certification', or 'membership'

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (builder_id) REFERENCES builder_profiles(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_builder_id (builder_id),
    INDEX idx_credential_type (credential_type),
    INDEX idx_builder_type (builder_id, credential_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add comment
ALTER TABLE builder_credentials COMMENT = 'Builder licenses, certifications, and memberships';


-- ===========================================================================
-- Sample Data (Optional - for testing)
-- ===========================================================================
-- Uncomment below to insert sample data for testing

-- Sample Builder Award
-- INSERT INTO builder_awards (
--     builder_id,
--     title,
--     issuer,
--     year
-- ) VALUES (
--     1,  -- Replace with actual builder_profiles.id
--     'Best Custom Home Builder',
--     'National Association of Home Builders',
--     2023
-- );

-- Sample Home Plan
-- INSERT INTO builder_home_plans (
--     builder_id,
--     name,
--     series,
--     sqft,
--     beds,
--     baths,
--     stories,
--     starting_price,
--     description
-- ) VALUES (
--     1,  -- Replace with actual builder_profiles.id
--     'The Oakmont',
--     'Executive Series',
--     3200,
--     4,
--     3.5,
--     2,
--     '650000.00',
--     'Spacious executive home with premium finishes and open floor plan'
-- );

-- Sample Credentials
-- INSERT INTO builder_credentials (builder_id, name, credential_type) VALUES
--     (1, 'General Contractor License #12345', 'license'),
--     (1, 'LEED Certified Professional', 'certification'),
--     (1, 'National Association of Home Builders', 'membership');
