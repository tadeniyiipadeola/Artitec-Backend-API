-- Migration: Create enterprise builder provisioning tables
-- Date: 2025-11-17
-- Description: Creates tables for enterprise builder account provisioning and team management
--              - enterprise_invitations: Track invitation codes for new team members
--              - builder_team_members: Manage multi-user access to builder profiles

-- ===========================================================================
-- Table: enterprise_invitations
-- ===========================================================================
CREATE TABLE IF NOT EXISTS enterprise_invitations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Unique invitation code (e.g., "X3P8Q1R9T2M4")
    invitation_code VARCHAR(64) NOT NULL UNIQUE,

    -- Builder this invitation is for (FK to builder_profiles.builder_id)
    builder_id VARCHAR(50) NOT NULL,

    -- Invited user details (before they register)
    invited_email VARCHAR(255) NOT NULL,
    invited_role ENUM('builder', 'salesrep', 'manager', 'viewer') NOT NULL DEFAULT 'builder',
    invited_first_name VARCHAR(120),
    invited_last_name VARCHAR(120),

    -- Who created this invitation (FK to users.user_id)
    created_by_user_id VARCHAR(50),

    -- Expiration and usage tracking
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    used_by_user_id VARCHAR(50) NULL,

    -- Status tracking
    status ENUM('pending', 'used', 'expired', 'revoked') NOT NULL DEFAULT 'pending',

    -- Optional custom message
    custom_message TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (builder_id) REFERENCES builder_profiles(builder_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (used_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL,

    -- Indexes
    INDEX idx_invitation_code (invitation_code),
    INDEX idx_builder_id (builder_id),
    INDEX idx_invited_email (invited_email),
    INDEX idx_builder_status (builder_id, status),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add comment
ALTER TABLE enterprise_invitations COMMENT = 'Enterprise builder invitation tracking for team members';


-- ===========================================================================
-- Table: builder_team_members
-- ===========================================================================
CREATE TABLE IF NOT EXISTS builder_team_members (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Builder this team member belongs to (FK to builder_profiles.builder_id)
    builder_id VARCHAR(50) NOT NULL,

    -- User account for this team member (FK to users.user_id)
    user_id VARCHAR(50) NOT NULL,

    -- Role within the builder organization
    role ENUM('admin', 'sales_rep', 'manager', 'viewer') NOT NULL DEFAULT 'sales_rep',

    -- Permissions (JSON array of permission keys)
    -- Examples: ["manage_properties", "invite_reps", "view_analytics"]
    permissions JSON NULL,

    -- Community assignments (JSON array of community IDs for sales reps)
    -- Examples: ["CMY-ABC123", "CMY-XYZ789"]
    -- NULL/empty = access to all communities
    communities_assigned JSON NULL,

    -- Who added this team member (FK to users.user_id)
    added_by_user_id VARCHAR(50) NULL,

    -- Status
    is_active ENUM('active', 'inactive') NOT NULL DEFAULT 'active',

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (builder_id) REFERENCES builder_profiles(builder_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL,

    -- Unique constraint: one user can only be on a builder's team once
    UNIQUE KEY uq_builder_team_member (builder_id, user_id),

    -- Indexes
    INDEX idx_builder_id (builder_id),
    INDEX idx_user_id (user_id),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add comment
ALTER TABLE builder_team_members COMMENT = 'Team member management for enterprise builder accounts';


-- ===========================================================================
-- Sample Data (Optional - for testing)
-- ===========================================================================
-- Uncomment below to insert sample invitation for testing

-- INSERT INTO enterprise_invitations (
--     invitation_code,
--     builder_id,
--     invited_email,
--     invited_role,
--     invited_first_name,
--     invited_last_name,
--     expires_at,
--     status
-- ) VALUES (
--     'SAMPLE123456',
--     'B_329_XXX_XXX_XXX_XXX',  -- Replace with actual builder_id
--     'john.smith@perryhomes.com',
--     'builder',
--     'John',
--     'Smith',
--     DATE_ADD(NOW(), INTERVAL 7 DAY),
--     'pending'
-- );
