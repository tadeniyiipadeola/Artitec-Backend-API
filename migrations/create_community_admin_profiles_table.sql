-- Migration: Create community_admin_profiles table
-- Date: 2025-11-09
-- Description: Creates table for linking users to communities they administer

CREATE TABLE IF NOT EXISTS community_admin_profiles (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- One-to-one with users.id
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,

    -- Links to the community this admin manages
    community_id BIGINT UNSIGNED NOT NULL,

    -- Profile/Display
    display_name VARCHAR(255),
    profile_image VARCHAR(500),  -- URL to profile image
    bio TEXT,
    title VARCHAR(128),  -- e.g., "HOA President", "Community Manager"

    -- Contact
    contact_email VARCHAR(255),
    contact_phone VARCHAR(64),
    contact_preferred VARCHAR(32),  -- "email", "phone", "sms", "in_app"

    -- Permissions
    can_post_announcements BOOLEAN NOT NULL DEFAULT TRUE,
    can_manage_events BOOLEAN NOT NULL DEFAULT TRUE,
    can_moderate_threads BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    extra TEXT,  -- JSON string for additional metadata

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_community_id (community_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add comment
ALTER TABLE community_admin_profiles COMMENT = 'Profiles for users who are community administrators';
