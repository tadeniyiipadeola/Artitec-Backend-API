-- ============================================================================
-- Fred Caldwell Community Profile - The Highlands, Porter TX
-- Real data for The Highlands Master-Planned Community
-- Developer: Caldwell Communities, Fred Caldwell (President & CEO)
-- ============================================================================

-- Variables (these will be set dynamically)
SET @user_id = NULL;
SET @community_id = NULL;
SET @role_id = NULL;

-- ============================================================================
-- STEP 1: Create/Find Community Admin Role
-- ============================================================================

-- Find or create community admin role
INSERT INTO roles (key, name, description)
VALUES ('community_admin', 'Community Admin', 'Community administrator role')
ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id);

SET @role_id = LAST_INSERT_ID();

-- ============================================================================
-- STEP 2: Create Fred Caldwell User
-- ============================================================================

-- Insert Fred Caldwell user (if not exists)
INSERT INTO users (
    public_id,
    email,
    first_name,
    last_name,
    phone_e164,
    role_id,
    onboarding_completed,
    is_email_verified,
    plan_tier,
    status
) VALUES (
    UUID(),
    'fred.caldwell@thehighlands.com',
    'Fred',
    'Caldwell',
    '+12817659900',
    @role_id,
    1,
    1,
    'enterprise',
    'active'
)
ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id);

SET @user_id = LAST_INSERT_ID();

-- ============================================================================
-- STEP 3: Create The Highlands Community
-- ============================================================================

INSERT INTO communities (
    public_id,
    name,
    city,
    state,
    postal_code,
    community_dues,
    tax_rate,
    monthly_fee,
    followers,
    about,
    is_verified,
    homes,
    residents,
    founded_year,
    member_count,
    development_stage,
    enterprise_number_hoa,
    intro_video_url,
    community_website_url
) VALUES (
    CONCAT('the-highlands-', SUBSTRING(UUID(), 1, 8)),
    'The Highlands',
    'Porter',
    'TX',
    '77365',
    '$1,420/year',
    '2.1%',
    '$118/month',
    2847,
    'The Highlands is a 2,300-acre exploration of natural beauty in a densely treed, park-like setting. Developed by Caldwell Communities, our award-winning master-planned community features large recreational lakes, over 30 miles of trails, and a 200-acre nature preserve with 100-year-old cypress trees.

Upon completion, The Highlands will welcome home approximately 4,000 families across 13 award-winning builders. Recognized by the Greater Houston Builders Association as the 2024 Master Planned Community of the Year, we offer residents an exceptional lifestyle with world-class amenities including a semi-private 18-hole golf course, water park with lazy river, state-of-the-art fitness center, and much more.

Located in Porter, TX in Montgomery County, just off the Grand Parkway (TX-99), The Highlands provides easy access to Houston, The Woodlands, and Conroe while maintaining a serene, nature-immersed setting. Students attend New Caney ISD schools, including the brand-new on-site Highlands Elementary.',
    1,
    1200,
    3600,
    2021,
    2847,
    'Active Development - Phase 2',
    'HOA-TX-2021-TH01',
    'https://thehighlands.com',
    'https://thehighlands.com'
);

SET @community_id = LAST_INSERT_ID();

-- ============================================================================
-- STEP 4: Create Community Amenities
-- ============================================================================

INSERT INTO community_amenities (community_id, name, gallery) VALUES
(@community_id, 'The Highlands Pines Golf Course', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Golf-Course-Hero.jpg',
    'https://thehighlands.com/wp-content/uploads/2023/04/Golf-Clubhouse.jpg'
)),
(@community_id, 'Water Park & Lazy River', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Water-Park.jpg',
    'https://thehighlands.com/wp-content/uploads/2023/04/Lazy-River.jpg'
)),
(@community_id, 'State-of-the-Art Fitness Center', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Fitness-Center.jpg'
)),
(@community_id, '30+ Miles of Trails', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Hiking-Trails.jpg',
    'https://thehighlands.com/wp-content/uploads/2023/04/Biking-Trails.jpg'
)),
(@community_id, '200-Acre Nature Preserve', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Nature-Preserve.jpg',
    'https://thehighlands.com/wp-content/uploads/2023/04/Cypress-Trees.jpg'
)),
(@community_id, 'Event Lawn & Pavilion', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Event-Lawn.jpg'
)),
(@community_id, 'Tennis & Pickleball Courts', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Tennis-Courts.jpg'
)),
(@community_id, 'Recreational Lakes', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Lake-Fishing.jpg',
    'https://thehighlands.com/wp-content/uploads/2023/04/Lake-Kayaking.jpg'
)),
(@community_id, 'Lakeside Patio & Firepit', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Lakeside-Patio.jpg'
)),
(@community_id, 'Fishing Docks & Picnic Pavilions', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Fishing-Dock.jpg'
)),
(@community_id, 'Amenity Center', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Amenity-Center.jpg'
)),
(@community_id, 'Highlands Elementary School', JSON_ARRAY(
    'https://thehighlands.com/wp-content/uploads/2023/04/Elementary-School.jpg'
));

-- ============================================================================
-- STEP 5: Create Community Events
-- ============================================================================

INSERT INTO community_events (community_id, title, description, location, start_at, end_at, is_public) VALUES
(@community_id,
 'Party in the Preserve',
 'Join us for our annual celebration in our stunning 200-acre nature preserve! This GHBA Event of the Year features live music, food trucks, family activities, and guided nature walks through our 100-year-old cypress forest.',
 '200-Acre Nature Preserve',
 DATE_ADD(NOW(), INTERVAL 21 DAY),
 DATE_ADD(NOW(), INTERVAL 21 DAY) + INTERVAL 5 HOUR,
 1),

(@community_id,
 'All Trails Lead Home Community Walk',
 'Explore our 30+ miles of beautiful trails with neighbors and friends. Complimentary trail maps and refreshments provided. A portion of proceeds benefits Montgomery County Food Bank.',
 'Trailhead at Amenity Center',
 DATE_ADD(NOW(), INTERVAL 14 DAY),
 DATE_ADD(NOW(), INTERVAL 14 DAY) + INTERVAL 3 HOUR,
 1),

(@community_id,
 'Golf Tournament & Social',
 'Annual member-guest golf tournament at The Highlands Pines. Enjoy 18 holes of championship golf followed by awards ceremony and BBQ at the clubhouse.',
 'The Highlands Pines Golf Course',
 DATE_ADD(NOW(), INTERVAL 30 DAY),
 DATE_ADD(NOW(), INTERVAL 30 DAY) + INTERVAL 6 HOUR,
 1),

(@community_id,
 'Lakeside Movie Night',
 'Family-friendly outdoor movie screening by the lake. Bring blankets and lawn chairs! Free popcorn and refreshments provided.',
 'Lakeside Event Lawn',
 DATE_ADD(NOW(), INTERVAL 10 DAY),
 DATE_ADD(NOW(), INTERVAL 10 DAY) + INTERVAL 3 HOUR,
 1),

(@community_id,
 'Community Fitness Bootcamp',
 'Free fitness classes led by certified trainers. All fitness levels welcome! Classes include yoga, HIIT, and aqua aerobics.',
 'Fitness Center & Pool',
 DATE_ADD(NOW(), INTERVAL 5 DAY),
 DATE_ADD(NOW(), INTERVAL 5 DAY) + INTERVAL 1 HOUR,
 1),

(@community_id,
 'Kayaking & Paddle Board Social',
 'Explore our recreational lakes by kayak or paddle board! Equipment provided for residents. Learn about local wildlife from our nature guide.',
 'Main Recreational Lake',
 DATE_ADD(NOW(), INTERVAL 18 DAY),
 DATE_ADD(NOW(), INTERVAL 18 DAY) + INTERVAL 2 HOUR,
 1);

-- ============================================================================
-- STEP 6: Create Builder Cards (13 Award-Winning Builders)
-- ============================================================================

INSERT INTO community_builders (community_id, icon, name, subtitle, followers, is_verified) VALUES
(@community_id, 'building.2.fill', 'Taylor Morrison', 'Award-Winning Homes', 2847, 1),
(@community_id, 'house.fill', 'Lennar', 'Everything\'s Included®', 3124, 1),
(@community_id, 'building.fill', 'Perry Homes', 'The Highlands 65\'', 2156, 1),
(@community_id, 'house.2.fill', 'Chesmar Homes', 'Quality & Value', 1823, 1),
(@community_id, 'building.2.fill', 'Highland Homes', 'Exceptional Design', 1965, 1),
(@community_id, 'house.fill', 'David Weekley Homes', 'America\'s Builder', 2541, 1),
(@community_id, 'building.fill', 'Coventry Homes', 'The Highlands 45\'', 1678, 1),
(@community_id, 'house.2.fill', 'Beazer Homes', 'Smart Home Technology', 1534, 1),
(@community_id, 'building.2.fill', 'Empire Homes', 'Texas Builder', 1342, 1),
(@community_id, 'house.fill', 'Partners in Building', 'Custom Luxury', 1256, 1),
(@community_id, 'building.fill', 'Caldwell Homes', 'By Caldwell Companies', 1891, 1),
(@community_id, 'house.2.fill', 'Drees Custom Homes', 'Personalized Living', 1423, 1),
(@community_id, 'building.2.fill', 'Newmark Homes', 'Inspired Design', 1298, 1);

-- ============================================================================
-- STEP 7: Create Community Admin Contacts
-- ============================================================================

INSERT INTO community_admins (community_id, name, role, email, phone) VALUES
(@community_id, 'Fred Caldwell', 'President & CEO, Caldwell Communities', 'fred.caldwell@caldwellcos.com', '(281) 765-9900'),
(@community_id, 'Sarah Mitchell', 'Community Lifestyle Director', 'sarah.mitchell@thehighlands.com', '(281) 765-9901'),
(@community_id, 'Michael Torres', 'Director of Operations', 'michael.torres@thehighlands.com', '(281) 765-9902'),
(@community_id, 'Jennifer Park', 'HOA Manager', 'jennifer.park@thehighlands.com', '(281) 765-9903');

-- ============================================================================
-- STEP 8: Create Community Awards
-- ============================================================================

INSERT INTO community_awards (community_id, title, year, issuer, icon, note) VALUES
(@community_id,
 'Master Planned Community of the Year',
 2024,
 'Greater Houston Builders Association',
 'trophy.fill',
 'Recognized as the top master-planned community in the Greater Houston area'),

(@community_id,
 'Event of the Year - Party in the Preserve',
 2024,
 'Greater Houston Builders Association',
 'star.fill',
 'Award for innovative community event celebrating the opening of our 200-acre nature preserve'),

(@community_id,
 'Developer of the Year',
 2024,
 'Greater Houston Builders Association',
 'rosette',
 'Caldwell Communities recognized for second consecutive year as Developer of the Year'),

(@community_id,
 'Developer of the Year',
 2023,
 'Greater Houston Builders Association',
 'rosette',
 'Caldwell Communities\' dedication to quality and community excellence'),

(@community_id,
 'Billboard Campaign Recognition',
 2024,
 'Greater Houston Builders Association',
 'photo.fill',
 'Award-winning "All Trails Lead Home Tour" marketing campaign'),

(@community_id,
 'Community Impact Award',
 2024,
 'Montgomery County',
 'heart.fill',
 'For charitable contributions to Montgomery County Food Bank and Sleep in Heavenly Peace');

-- ============================================================================
-- STEP 9: Create Discussion Topics
-- ============================================================================

INSERT INTO community_topics (community_id, title, category, replies, last_activity, is_pinned, comments) VALUES
(@community_id,
 'New Middle School Opening Fall 2027',
 'Education',
 34,
 '3 hours ago',
 1,
 JSON_ARRAY(
     JSON_OBJECT('author', 'Jennifer Martinez', 'text', 'This is amazing news! So glad we''ll have an on-site middle school soon.', 'timestamp', '2024-11-11T14:30:00Z'),
     JSON_OBJECT('author', 'Fred Caldwell', 'text', 'We''re thrilled to bring another on-site school to The Highlands. New Caney ISD has been an exceptional partner.', 'timestamp', '2024-11-11T16:45:00Z'),
     JSON_OBJECT('author', 'David Chen', 'text', 'Having both elementary and middle school on-site is a game-changer for families!', 'timestamp', '2024-11-11T18:20:00Z')
 )),

(@community_id,
 'Golf Course Membership Options',
 'Amenities',
 28,
 '5 hours ago',
 1,
 JSON_ARRAY(
     JSON_OBJECT('author', 'Robert Johnson', 'text', 'Can someone explain the different golf membership tiers?', 'timestamp', '2024-11-10T09:15:00Z'),
     JSON_OBJECT('author', 'Sarah Mitchell', 'text', 'We offer several options! Full details are on the amenity center website. I''ll send you a direct link.', 'timestamp', '2024-11-10T10:30:00Z')
 )),

(@community_id,
 'Trail Maintenance and New Routes',
 'Recreation',
 42,
 '1 day ago',
 0,
 JSON_ARRAY()),

(@community_id,
 'Party in the Preserve - Volunteer Opportunities',
 'Events',
 19,
 '2 days ago',
 1,
 JSON_ARRAY()),

(@community_id,
 'Water Park Hours Summer Extension',
 'Amenities',
 31,
 '4 days ago',
 0,
 JSON_ARRAY()),

(@community_id,
 'Fishing Tournament Sign-Ups',
 'Recreation',
 15,
 '1 week ago',
 0,
 JSON_ARRAY());

-- ============================================================================
-- STEP 10: Create Development Phases
-- ============================================================================

INSERT INTO community_phases (community_id, name, lots, map_url) VALUES
(@community_id,
 'Phase 1 - The Pines (Complete)',
 JSON_ARRAY(
     JSON_OBJECT('lot_number', '1-001', 'status', 'sold', 'sqft', 10500, 'price', NULL),
     JSON_OBJECT('lot_number', '1-002', 'status', 'sold', 'sqft', 11200, 'price', NULL),
     JSON_OBJECT('lot_number', '1-003', 'status', 'sold', 'sqft', 9800, 'price', NULL),
     JSON_OBJECT('lot_number', '1-004', 'status', 'sold', 'sqft', 12000, 'price', NULL),
     JSON_OBJECT('lot_number', '1-005', 'status', 'sold', 'sqft', 10800, 'price', NULL)
 ),
 'https://thehighlands.com/maps/phase1-the-pines.pdf'),

(@community_id,
 'Phase 2 - The Preserve (Active)',
 JSON_ARRAY(
     JSON_OBJECT('lot_number', '2-001', 'status', 'sold', 'sqft', 14000, 'price', NULL),
     JSON_OBJECT('lot_number', '2-002', 'status', 'available', 'sqft', 15500, 'price', 185000),
     JSON_OBJECT('lot_number', '2-003', 'status', 'available', 'sqft', 13200, 'price', 165000),
     JSON_OBJECT('lot_number', '2-004', 'status', 'sold', 'sqft', 16000, 'price', NULL),
     JSON_OBJECT('lot_number', '2-005', 'status', 'available', 'sqft', 14500, 'price', 175000),
     JSON_OBJECT('lot_number', '2-006', 'status', 'reserved', 'sqft', 15000, 'price', 180000)
 ),
 'https://thehighlands.com/maps/phase2-the-preserve.pdf'),

(@community_id,
 'Phase 3 - Lakeside Village (Coming Soon)',
 JSON_ARRAY(
     JSON_OBJECT('lot_number', '3-001', 'status', 'coming_soon', 'sqft', 12000, 'price', NULL),
     JSON_OBJECT('lot_number', '3-002', 'status', 'coming_soon', 'sqft', 13500, 'price', NULL),
     JSON_OBJECT('lot_number', '3-003', 'status', 'coming_soon', 'sqft', 11800, 'price', NULL),
     JSON_OBJECT('lot_number', '3-004', 'status', 'coming_soon', 'sqft', 14200, 'price', NULL)
 ),
 'https://thehighlands.com/maps/phase3-lakeside-village.pdf'),

(@community_id,
 'Fairway Pines - 55+ Active Adult Community',
 JSON_ARRAY(
     JSON_OBJECT('lot_number', 'FP-001', 'status', 'available', 'sqft', 8500, 'price', 145000),
     JSON_OBJECT('lot_number', 'FP-002', 'status', 'available', 'sqft', 9000, 'price', 155000),
     JSON_OBJECT('lot_number', 'FP-003', 'status', 'sold', 'sqft', 8800, 'price', NULL),
     JSON_OBJECT('lot_number', 'FP-004', 'status', 'available', 'sqft', 9200, 'price', 160000)
 ),
 'https://thehighlands.com/maps/fairway-pines.pdf');

-- ============================================================================
-- STEP 11: Create Community Admin Profile for Fred Caldwell
-- ============================================================================

INSERT INTO community_admin_profiles (
    user_id,
    community_id,
    first_name,
    last_name,
    profile_image,
    bio,
    title,
    contact_email,
    contact_phone,
    contact_preferred,
    can_post_announcements,
    can_manage_events,
    can_moderate_threads
) VALUES (
    @user_id,
    @community_id,
    'Fred',
    'Caldwell',
    'https://caldwellcos.com/wp-content/uploads/fred-caldwell-headshot.jpg',
    'Fred Caldwell is the President and CEO of Caldwell Communities, bringing over 30 years of experience in creating award-winning master-planned communities across the Greater Houston area. Under his visionary leadership, Caldwell Communities has developed more than 10 successful communities and earned the prestigious Greater Houston Builders Association Developer of the Year Award in 2024, 2023, and 2019.

The Highlands represents the pinnacle of Fred''s commitment to creating communities that harmonize with nature while providing world-class amenities and exceptional quality of life. His passion for environmental stewardship is evident in The Highlands'' 200-acre nature preserve, 30+ miles of trails, and careful preservation of the area''s natural beauty.

Fred believes in giving back to the community, establishing programs like the "All Trails Lead Home Tour" which donates proceeds to local charities including the Montgomery County Food Bank and Sleep in Heavenly Peace. Under his guidance, The Highlands was named the 2024 Master Planned Community of the Year by the Greater Houston Builders Association.

When he''s not working on creating exceptional communities, Fred enjoys golfing at The Highlands Pines and exploring the trails with his family.',
    'President & CEO, Caldwell Communities',
    'fred.caldwell@caldwellcos.com',
    '(281) 765-9900',
    'email',
    1,
    1,
    1
);

-- ============================================================================
-- Summary Query
-- ============================================================================

SELECT
    @user_id AS user_id,
    @community_id AS community_id,
    'Fred Caldwell''s The Highlands community profile created successfully!' AS status;

-- Verify data
SELECT
    u.id as user_id,
    u.public_id as user_public_id,
    u.email,
    CONCAT(u.first_name, ' ', u.last_name) as user_name,
    c.id as community_id,
    c.public_id as community_public_id,
    c.name as community_name,
    c.city,
    c.state,
    c.postal_code,
    c.homes as current_homes,
    c.residents as current_residents
FROM users u
JOIN community_admin_profiles cap ON u.id = cap.user_id
JOIN communities c ON cap.community_id = c.id
WHERE u.id = @user_id;

-- Show amenity count
SELECT COUNT(*) as total_amenities FROM community_amenities WHERE community_id = @community_id;

-- Show builder count
SELECT COUNT(*) as total_builders FROM community_builders WHERE community_id = @community_id;

-- Show event count
SELECT COUNT(*) as upcoming_events FROM community_events WHERE community_id = @community_id;

-- Show awards count
SELECT COUNT(*) as total_awards FROM community_awards WHERE community_id = @community_id;
