-- ============================================================================
-- Create Community Admin Profile for user USR-1763002155-GRZVLL
-- Links the user to The Highlands community
-- ============================================================================

-- First, verify the user exists and get their information
SELECT id, user_id, email, first_name, last_name, role
FROM users
WHERE user_id = 'USR-1763002155-GRZVLL';

-- Verify The Highlands community exists
SELECT id, community_id, name, city, state
FROM communities
WHERE name = 'The Highlands';

-- Insert the community admin profile
-- Note: Replace @community_admin_id with a generated ID in format: ADM-TIMESTAMP-RANDOM
-- Example: ADM-1731518400-X7Y8Z9

SET @generated_id = CONCAT('ADM-', UNIX_TIMESTAMP(), '-', UPPER(SUBSTRING(MD5(RAND()), 1, 6)));

INSERT INTO community_admin_profiles (
    community_admin_id,
    user_id,
    community_id,
    first_name,
    last_name,
    title,
    contact_email,
    contact_phone,
    contact_preferred,
    can_post_announcements,
    can_manage_events,
    can_moderate_threads
)
SELECT
    @generated_id,
    u.user_id,
    c.id,
    u.first_name,
    u.last_name,
    'Community Admin',
    u.email,
    u.phone_e164,
    'email',
    TRUE,
    TRUE,
    TRUE
FROM users u
CROSS JOIN communities c
WHERE u.user_id = 'USR-1763002155-GRZVLL'
AND c.name = 'The Highlands';

-- Verify the insert
SELECT
    cap.id,
    cap.community_admin_id,
    cap.user_id,
    cap.community_id,
    cap.first_name,
    cap.last_name,
    cap.title,
    c.name as community_name
FROM community_admin_profiles cap
JOIN communities c ON cap.community_id = c.id
WHERE cap.user_id = 'USR-1763002155-GRZVLL';
