-- ============================================================================
-- Community Profile Tables - Complete Schema
-- This creates the main communities table and all related tables
-- ============================================================================

-- ============================================================================
-- MAIN COMMUNITY PROFILE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS communities (
    -- Primary Key
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Unique identifier (mirrors Swift UUID)
    public_id VARCHAR(64) NOT NULL UNIQUE,

    -- Basic Information
    name VARCHAR(255) NOT NULL,
    city VARCHAR(255),
    postal_code VARCHAR(20),

    -- Finance Information
    community_dues VARCHAR(64),
    tax_rate VARCHAR(32),
    monthly_fee VARCHAR(64),

    -- Header & Meta
    followers INT DEFAULT 0,
    about TEXT,
    is_verified BOOLEAN DEFAULT FALSE,

    -- Statistics
    homes INT DEFAULT 0,
    residents INT DEFAULT 0,
    founded_year INT,
    member_count INT DEFAULT 0,

    -- Media
    intro_video_url VARCHAR(1024),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_public_id (public_id),
    INDEX idx_name (name),
    INDEX idx_city (city)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- AMENITIES TABLE (Pool, Gym, Trails, etc.)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_amenities (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Amenity Info
    name VARCHAR(255) NOT NULL,
    gallery JSON,  -- Array of image URLs

    -- Foreign Key
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_community_id (community_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- EVENTS TABLE (Upcoming community events)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Event Info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP,
    is_public BOOLEAN DEFAULT TRUE NOT NULL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign Key
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_community_id (community_id),
    INDEX idx_start_at (start_at)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- BUILDER CARDS TABLE (Builders working in this community)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_builders (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Builder Info
    icon VARCHAR(64),  -- SF Symbol name
    name VARCHAR(255),
    subtitle VARCHAR(255),
    followers INT DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,

    -- Foreign Key
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_community_id (community_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- ADMINS TABLE (Community admin contact information)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_admins (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Admin Info
    name VARCHAR(255),
    role VARCHAR(128),
    email VARCHAR(255),
    phone VARCHAR(64),

    -- Foreign Key
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_community_id (community_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- AWARDS TABLE (Recognition and awards)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_awards (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Award Info
    title VARCHAR(255),
    year INT,
    issuer VARCHAR(255),
    icon VARCHAR(64),  -- SF Symbol name
    note TEXT,

    -- Foreign Key
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_community_id (community_id),
    INDEX idx_year (year)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- TOPICS TABLE (Discussion threads)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_topics (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Topic Info
    title VARCHAR(255),
    category VARCHAR(255),
    replies INT DEFAULT 0,
    last_activity VARCHAR(128),
    is_pinned BOOLEAN DEFAULT FALSE,
    comments JSON,  -- Array of comment objects

    -- Foreign Key
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_community_id (community_id),
    INDEX idx_is_pinned (is_pinned)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- PHASES TABLE (Development phases with lots)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_phases (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Phase Info
    name VARCHAR(255),
    lots JSON,  -- Array of lot objects (lot_number, status, sqft, price)
    map_url VARCHAR(1024),

    -- Foreign Key
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_community_id (community_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- COMMUNITY ADMIN PROFILES TABLE (Links users to communities)
-- ============================================================================

CREATE TABLE IF NOT EXISTS community_admin_profiles (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Links to user and community
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    community_id BIGINT UNSIGNED NOT NULL,

    -- Profile/Display
    display_name VARCHAR(255),
    profile_image VARCHAR(500),
    bio TEXT,
    title VARCHAR(128),

    -- Contact
    contact_email VARCHAR(255),
    contact_phone VARCHAR(64),
    contact_preferred VARCHAR(32),

    -- Permissions
    can_post_announcements BOOLEAN NOT NULL DEFAULT TRUE,
    can_manage_events BOOLEAN NOT NULL DEFAULT TRUE,
    can_moderate_threads BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    extra TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_community_id (community_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Add table comments
-- ============================================================================

ALTER TABLE communities COMMENT = 'Main community profile table';
ALTER TABLE community_amenities COMMENT = 'Community amenities (pool, gym, trails, etc.)';
ALTER TABLE community_events COMMENT = 'Upcoming community events';
ALTER TABLE community_builders COMMENT = 'Builders working in this community';
ALTER TABLE community_admins COMMENT = 'Community administrator contact info';
ALTER TABLE community_awards COMMENT = 'Recognition and awards';
ALTER TABLE community_topics COMMENT = 'Discussion threads and topics';
ALTER TABLE community_phases COMMENT = 'Development phases with lot information';
ALTER TABLE community_admin_profiles COMMENT = 'Links users to communities they manage';


-- ============================================================================
-- Sample data inserts (optional - uncomment to use)
-- ============================================================================

/*
-- Insert a sample community
INSERT INTO communities (
    public_id, name, city, postal_code,
    community_dues, tax_rate, monthly_fee,
    followers, about, is_verified,
    homes, residents, founded_year, member_count
) VALUES (
    'oak-meadows-001',
    'Oak Meadows',
    'Austin',
    '78704',
    '$500/year',
    '2.1%',
    '$125',
    1250,
    'Oak Meadows is a vibrant, family-friendly community nestled in the heart of Austin, Texas.',
    1,
    524,
    1847,
    2018,
    1250
);

-- Get the community ID
SET @community_id = LAST_INSERT_ID();

-- Insert sample amenities
INSERT INTO community_amenities (community_id, name, gallery) VALUES
(@community_id, 'Resort-Style Pool', JSON_ARRAY('/uploads/amenities/pool1.jpg', '/uploads/amenities/pool2.jpg')),
(@community_id, 'Fitness Center', JSON_ARRAY('/uploads/amenities/gym1.jpg')),
(@community_id, 'Walking Trails', JSON_ARRAY('/uploads/amenities/trails1.jpg'));

-- Insert sample admin
INSERT INTO community_admins (community_id, name, role, email, phone) VALUES
(@community_id, 'Sarah Johnson', 'HOA President', 'sarah.johnson@oakmeadows.org', '(512) 555-0123');

-- Insert sample award
INSERT INTO community_awards (community_id, title, year, issuer, icon, note) VALUES
(@community_id, 'Best Master-Planned Community', 2023, 'Austin Home Builders Association', 'rosette', 'Awarded for outstanding community design');
*/
