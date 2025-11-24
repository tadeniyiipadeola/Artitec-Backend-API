-- ============================================================================
-- SQL QUERIES FOR KELLE GANDY ENTERPRISE ACCOUNT VERIFICATION
-- ============================================================================
-- Database: appdb (MariaDB)
-- Purpose: Verify Kelle Gandy's access to Perry Homes builder profiles
-- ============================================================================

-- 1. FIND KELLE GANDY'S USER RECORD
-- ============================================================================
SELECT
    user_id,
    email,
    role,
    plan_tier,
    first_name,
    last_name,
    onboarding_completed,
    status,
    created_at
FROM users
WHERE email = 'kelle.gandy@perryhomes.com';

-- Expected Result:
-- user_id: USR-11CF01A81A08
-- email: kelle.gandy@perryhomes.com
-- role: builder
-- plan_tier: enterprise


-- 2. BUILDER PROFILES OWNED BY KELLE (user_id match)
-- ============================================================================
SELECT
    id,
    builder_id,
    name,
    city,
    state,
    verified,
    rating,
    website,
    created_at
FROM builder_profiles
WHERE user_id = 'USR-11CF01A81A08'
ORDER BY city;

-- Expected Result: 18 Perry Homes profiles


-- 3. TEAM MEMBERSHIPS FOR KELLE
-- ============================================================================
SELECT
    btm.id,
    btm.builder_id,
    btm.role,
    btm.permissions,
    btm.communities_assigned,
    btm.is_active,
    bp.name,
    bp.city,
    bp.state
FROM builder_team_members btm
LEFT JOIN builder_profiles bp ON btm.builder_id = bp.builder_id
WHERE btm.user_id = 'USR-11CF01A81A08'
  AND btm.is_active = 'active';

-- Expected Result: 0 team memberships (Kelle owns all profiles directly)


-- 4. ALL ACCESSIBLE PROFILES (OWNED + TEAM MEMBER) - UNION QUERY
-- ============================================================================
-- This is what the endpoint GET /v1/profiles/builders/me/profiles should return

SELECT DISTINCT
    bp.id,
    bp.builder_id,
    bp.name,
    bp.city,
    bp.state,
    bp.verified,
    bp.rating,
    bp.user_id,
    'owned' as access_type
FROM builder_profiles bp
WHERE bp.user_id = 'USR-11CF01A81A08'

UNION

SELECT DISTINCT
    bp.id,
    bp.builder_id,
    bp.name,
    bp.city,
    bp.state,
    bp.verified,
    bp.rating,
    bp.user_id,
    'team_member' as access_type
FROM builder_profiles bp
INNER JOIN builder_team_members btm ON bp.builder_id = btm.builder_id
WHERE btm.user_id = 'USR-11CF01A81A08'
  AND btm.is_active = 'active'

ORDER BY name, city;

-- Expected Result: 18 total profiles


-- 5. VERIFY ALL PERRY HOMES PROFILES
-- ============================================================================
SELECT
    id,
    builder_id,
    name,
    city,
    state,
    verified,
    user_id,
    created_at
FROM builder_profiles
WHERE name LIKE '%Perry%'
ORDER BY city;

-- Expected Result: All should have user_id = 'USR-11CF01A81A08'


-- 6. COUNT VERIFICATION
-- ============================================================================
-- Count profiles owned by Kelle
SELECT COUNT(*) as owned_profiles
FROM builder_profiles
WHERE user_id = 'USR-11CF01A81A08';

-- Count team memberships
SELECT COUNT(*) as team_memberships
FROM builder_team_members
WHERE user_id = 'USR-11CF01A81A08'
  AND is_active = 'active';

-- Total accessible profiles (should be 18)
SELECT COUNT(DISTINCT bp.builder_id) as total_accessible
FROM builder_profiles bp
LEFT JOIN builder_team_members btm
    ON bp.builder_id = btm.builder_id
    AND btm.user_id = 'USR-11CF01A81A08'
    AND btm.is_active = 'active'
WHERE bp.user_id = 'USR-11CF01A81A08'
   OR btm.id IS NOT NULL;


-- 7. SAMPLE PROFILE DATA (3 profiles with details)
-- ============================================================================
SELECT
    id,
    builder_id,
    name,
    city,
    state,
    verified,
    rating,
    website,
    email,
    phone,
    about
FROM builder_profiles
WHERE user_id = 'USR-11CF01A81A08'
LIMIT 3;


-- 8. CHECK FOR ORPHANED TEAM MEMBERSHIPS
-- ============================================================================
-- Team memberships pointing to non-existent builder profiles
SELECT
    btm.id,
    btm.builder_id,
    btm.user_id,
    btm.role
FROM builder_team_members btm
LEFT JOIN builder_profiles bp ON btm.builder_id = bp.builder_id
WHERE bp.id IS NULL;

-- Expected Result: 0 orphaned records


-- 9. VERIFY BUILDER_ID UNIQUENESS
-- ============================================================================
-- Check for duplicate builder_ids (should be 0)
SELECT
    builder_id,
    COUNT(*) as count
FROM builder_profiles
GROUP BY builder_id
HAVING count > 1;


-- 10. DETAILED PROFILE LISTING FOR KELLE
-- ============================================================================
-- All 18 profiles with complete details
SELECT
    ROW_NUMBER() OVER (ORDER BY city) as row_num,
    id,
    builder_id,
    name,
    city,
    state,
    verified,
    rating,
    website,
    email,
    phone,
    created_at
FROM builder_profiles
WHERE user_id = 'USR-11CF01A81A08'
ORDER BY city;
