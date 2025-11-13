"""seed The Highlands community data

Revision ID: d1e2f3g4h5i6
Revises: b1c2d3e4f5g6
Create Date: 2025-11-12 14:00:00.000000

Seeds complete data for The Highlands master-planned community in Porter, TX
with Fred Caldwell as President & CEO of Caldwell Communities.
"""
from typing import Sequence, Union
from datetime import datetime, timedelta

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3g4h5i6'
down_revision: Union[str, None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed The Highlands community data"""

    conn = op.get_bind()

    print("Seeding The Highlands community data...")
    print("=" * 60)

    # ========================================================================
    # STEP 1: Create/Find Community Admin Role
    # ========================================================================
    print("\nStep 1: Setting up community admin role...")

    conn.execute(text("""
        INSERT INTO roles (`key`, name, description)
        VALUES ('community_admin', 'Community Admin', 'Community administrator role')
        ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
    """))

    role_result = conn.execute(text("SELECT LAST_INSERT_ID() as role_id"))
    role_id = role_result.fetchone()[0]
    print(f"✓ Community admin role ID: {role_id}")

    # ========================================================================
    # STEP 2: Create Fred Caldwell User
    # ========================================================================
    print("\nStep 2: Creating Fred Caldwell user...")

    # Check if user already exists
    user_check = conn.execute(text("""
        SELECT id FROM users WHERE email = 'fred.caldwell@thehighlands.com'
    """))
    existing_user = user_check.fetchone()

    if existing_user:
        user_id = existing_user[0]
        print(f"✓ User already exists (ID: {user_id})")
    else:
        conn.execute(text("""
            INSERT INTO users (
                public_id, email, first_name, last_name, phone_e164,
                role_id, onboarding_completed, is_email_verified, plan_tier, status
            ) VALUES (
                UUID(), 'fred.caldwell@thehighlands.com', 'Fred', 'Caldwell', '+12817659900',
                :role_id, 1, 1, 'enterprise', 'active'
            )
        """), {"role_id": role_id})

        user_result = conn.execute(text("SELECT LAST_INSERT_ID() as user_id"))
        user_id = user_result.fetchone()[0]
        print(f"✓ Created Fred Caldwell (ID: {user_id})")

    # ========================================================================
    # STEP 3: Create The Highlands Community
    # ========================================================================
    print("\nStep 3: Creating The Highlands community...")

    # Check if community already exists
    comm_check = conn.execute(text("""
        SELECT id FROM communities WHERE name = 'The Highlands' AND city = 'Porter'
    """))
    existing_comm = comm_check.fetchone()

    if existing_comm:
        community_id = existing_comm[0]
        print(f"✓ Community already exists (ID: {community_id})")
    else:
        conn.execute(text("""
            INSERT INTO communities (
                public_id, name, city, state, postal_code,
                community_dues, tax_rate, monthly_fee, followers, about,
                homes, residents, founded_year, member_count, development_stage,
                enterprise_number_hoa, intro_video_url, community_website_url
            ) VALUES (
                CONCAT('the-highlands-', SUBSTRING(UUID(), 1, 8)),
                'The Highlands', 'Porter', 'TX', '77365',
                '$1,420/year', '2.1%%', '$118/month', 2847,
                'The Highlands is a 2,300-acre exploration of natural beauty in a densely treed, park-like setting. Developed by Caldwell Communities, our award-winning master-planned community features large recreational lakes, over 30 miles of trails, and a 200-acre nature preserve with 100-year-old cypress trees.

Upon completion, The Highlands will welcome home approximately 4,000 families across 13 award-winning builders. Recognized by the Greater Houston Builders Association as the 2024 Master Planned Community of the Year, we offer residents an exceptional lifestyle with world-class amenities including a semi-private 18-hole golf course, water park with lazy river, state-of-the-art fitness center, and much more.

Located in Porter, TX in Montgomery County, just off the Grand Parkway (TX-99), The Highlands provides easy access to Houston, The Woodlands, and Conroe while maintaining a serene, nature-immersed setting. Students attend New Caney ISD schools, including the brand-new on-site Highlands Elementary.',
                1200, 3600, 2021, 2847, 'Active Development - Phase 2',
                'HOA-TX-2021-TH01', 'https://thehighlands.com', 'https://thehighlands.com'
            )
        """))

        comm_result = conn.execute(text("SELECT LAST_INSERT_ID() as community_id"))
        community_id = comm_result.fetchone()[0]
        print(f"✓ Created The Highlands (ID: {community_id})")

    # ========================================================================
    # STEP 4: Create Amenities
    # ========================================================================
    print("\nStep 4: Creating 12 amenities...")

    amenities = [
        ('The Highlands Pines Golf Course', '["https://thehighlands.com/wp-content/uploads/2023/04/Golf-Course-Hero.jpg"]'),
        ('Water Park & Lazy River', '["https://thehighlands.com/wp-content/uploads/2023/04/Water-Park.jpg"]'),
        ('State-of-the-Art Fitness Center', '["https://thehighlands.com/wp-content/uploads/2023/04/Fitness-Center.jpg"]'),
        ('30+ Miles of Trails', '["https://thehighlands.com/wp-content/uploads/2023/04/Hiking-Trails.jpg"]'),
        ('200-Acre Nature Preserve', '["https://thehighlands.com/wp-content/uploads/2023/04/Nature-Preserve.jpg"]'),
        ('Event Lawn & Pavilion', '["https://thehighlands.com/wp-content/uploads/2023/04/Event-Lawn.jpg"]'),
        ('Tennis & Pickleball Courts', '["https://thehighlands.com/wp-content/uploads/2023/04/Tennis-Courts.jpg"]'),
        ('Recreational Lakes', '["https://thehighlands.com/wp-content/uploads/2023/04/Lake-Fishing.jpg"]'),
        ('Lakeside Patio & Firepit', '["https://thehighlands.com/wp-content/uploads/2023/04/Lakeside-Patio.jpg"]'),
        ('Fishing Docks & Picnic Pavilions', '["https://thehighlands.com/wp-content/uploads/2023/04/Fishing-Dock.jpg"]'),
        ('Amenity Center', '["https://thehighlands.com/wp-content/uploads/2023/04/Amenity-Center.jpg"]'),
        ('Highlands Elementary School', '["https://thehighlands.com/wp-content/uploads/2023/04/Elementary-School.jpg"]')
    ]

    for name, gallery in amenities:
        conn.execute(text("""
            INSERT INTO community_amenities (community_id, name, gallery)
            VALUES (:community_id, :name, :gallery)
            ON DUPLICATE KEY UPDATE name=name
        """), {"community_id": community_id, "name": name, "gallery": gallery})

    print(f"✓ Created {len(amenities)} amenities")

    # ========================================================================
    # STEP 5: Create Events
    # ========================================================================
    print("\nStep 5: Creating 6 community events...")

    now = datetime.utcnow()
    events = [
        ('Party in the Preserve', 'GHBA Event of the Year celebration in our stunning 200-acre nature preserve!', '200-Acre Nature Preserve', 21, 5),
        ('All Trails Lead Home Community Walk', 'Explore our 30+ miles of beautiful trails. Proceeds benefit Montgomery County Food Bank.', 'Trailhead at Amenity Center', 14, 3),
        ('Golf Tournament & Social', 'Annual member-guest tournament at The Highlands Pines. BBQ and awards ceremony.', 'The Highlands Pines Golf Course', 30, 6),
        ('Lakeside Movie Night', 'Family-friendly outdoor movie by the lake. Free popcorn and refreshments!', 'Lakeside Event Lawn', 10, 3),
        ('Community Fitness Bootcamp', 'Free classes: yoga, HIIT, aqua aerobics. All fitness levels welcome!', 'Fitness Center & Pool', 5, 1),
        ('Kayaking & Paddle Board Social', 'Equipment provided for residents. Learn about local wildlife!', 'Main Recreational Lake', 18, 2)
    ]

    for title, desc, location, days_offset, hours_duration in events:
        start_date = now + timedelta(days=days_offset)
        end_date = start_date + timedelta(hours=hours_duration)

        conn.execute(text("""
            INSERT INTO community_events (community_id, title, description, location, start_at, end_at, is_public)
            VALUES (:community_id, :title, :desc, :location, :start_at, :end_at, 1)
            ON DUPLICATE KEY UPDATE title=title
        """), {
            "community_id": community_id,
            "title": title,
            "desc": desc,
            "location": location,
            "start_at": start_date,
            "end_at": end_date
        })

    print(f"✓ Created {len(events)} events")

    # ========================================================================
    # STEP 6: Create Builder Cards
    # ========================================================================
    print("\nStep 6: Creating 13 builder cards...")

    builders = [
        ('building.2.fill', 'Taylor Morrison', 'Award-Winning Homes', 2847),
        ('house.fill', 'Lennar', 'Everything\'s Included®', 3124),
        ('building.fill', 'Perry Homes', 'The Highlands 65\'', 2156),
        ('house.2.fill', 'Chesmar Homes', 'Quality & Value', 1823),
        ('building.2.fill', 'Highland Homes', 'Exceptional Design', 1965),
        ('house.fill', 'David Weekley Homes', 'America\'s Builder', 2541),
        ('building.fill', 'Coventry Homes', 'The Highlands 45\'', 1678),
        ('house.2.fill', 'Beazer Homes', 'Smart Home Technology', 1534),
        ('building.2.fill', 'Empire Homes', 'Texas Builder', 1342),
        ('house.fill', 'Partners in Building', 'Custom Luxury', 1256),
        ('building.fill', 'Caldwell Homes', 'By Caldwell Companies', 1891),
        ('house.2.fill', 'Drees Custom Homes', 'Personalized Living', 1423),
        ('building.2.fill', 'Newmark Homes', 'Inspired Design', 1298)
    ]

    for icon, name, subtitle, followers in builders:
        conn.execute(text("""
            INSERT INTO community_builders (community_id, icon, name, subtitle, followers, is_verified)
            VALUES (:community_id, :icon, :name, :subtitle, :followers, 1)
            ON DUPLICATE KEY UPDATE name=name
        """), {
            "community_id": community_id,
            "icon": icon,
            "name": name,
            "subtitle": subtitle,
            "followers": followers
        })

    print(f"✓ Created {len(builders)} builder cards")

    # ========================================================================
    # STEP 7: Create Admin Contacts
    # ========================================================================
    print("\nStep 7: Creating 4 admin contacts...")

    admins = [
        ('Fred Caldwell', 'President & CEO, Caldwell Communities', 'fred.caldwell@caldwellcos.com', '(281) 765-9900'),
        ('Sarah Mitchell', 'Community Lifestyle Director', 'sarah.mitchell@thehighlands.com', '(281) 765-9901'),
        ('Michael Torres', 'Director of Operations', 'michael.torres@thehighlands.com', '(281) 765-9902'),
        ('Jennifer Park', 'HOA Manager', 'jennifer.park@thehighlands.com', '(281) 765-9903')
    ]

    for name, role, email, phone in admins:
        conn.execute(text("""
            INSERT INTO community_admins (community_id, name, role, email, phone)
            VALUES (:community_id, :name, :role, :email, :phone)
            ON DUPLICATE KEY UPDATE name=name
        """), {
            "community_id": community_id,
            "name": name,
            "role": role,
            "email": email,
            "phone": phone
        })

    print(f"✓ Created {len(admins)} admin contacts")

    # ========================================================================
    # STEP 8: Create Awards
    # ========================================================================
    print("\nStep 8: Creating 6 awards...")

    awards = [
        ('Master Planned Community of the Year', 2024, 'Greater Houston Builders Association', 'trophy.fill', 'Top master-planned community in Greater Houston'),
        ('Event of the Year - Party in the Preserve', 2024, 'Greater Houston Builders Association', 'star.fill', 'Innovative community event celebrating nature preserve'),
        ('Developer of the Year', 2024, 'Greater Houston Builders Association', 'rosette', 'Second consecutive year recognition'),
        ('Developer of the Year', 2023, 'Greater Houston Builders Association', 'rosette', 'Dedication to quality and community excellence'),
        ('Billboard Campaign Recognition', 2024, 'Greater Houston Builders Association', 'photo.fill', 'Award-winning "All Trails Lead Home Tour"'),
        ('Community Impact Award', 2024, 'Montgomery County', 'heart.fill', 'Charitable contributions to local organizations')
    ]

    for title, year, issuer, icon, note in awards:
        conn.execute(text("""
            INSERT INTO community_awards (community_id, title, year, issuer, icon, note)
            VALUES (:community_id, :title, :year, :issuer, :icon, :note)
            ON DUPLICATE KEY UPDATE title=title
        """), {
            "community_id": community_id,
            "title": title,
            "year": year,
            "issuer": issuer,
            "icon": icon,
            "note": note
        })

    print(f"✓ Created {len(awards)} awards")

    # ========================================================================
    # STEP 9: Create Discussion Topics
    # ========================================================================
    print("\nStep 9: Creating 6 discussion topics...")

    topics = [
        ('New Middle School Opening Fall 2027', 'Education', 34, '3 hours ago', 1),
        ('Golf Course Membership Options', 'Amenities', 28, '5 hours ago', 1),
        ('Trail Maintenance and New Routes', 'Recreation', 42, '1 day ago', 0),
        ('Party in the Preserve - Volunteer Opportunities', 'Events', 19, '2 days ago', 1),
        ('Water Park Hours Summer Extension', 'Amenities', 31, '4 days ago', 0),
        ('Fishing Tournament Sign-Ups', 'Recreation', 15, '1 week ago', 0)
    ]

    for title, category, replies, last_activity, is_pinned in topics:
        conn.execute(text("""
            INSERT INTO community_topics (community_id, title, category, replies, last_activity, is_pinned, comments)
            VALUES (:community_id, :title, :category, :replies, :last_activity, :is_pinned, '[]')
            ON DUPLICATE KEY UPDATE title=title
        """), {
            "community_id": community_id,
            "title": title,
            "category": category,
            "replies": replies,
            "last_activity": last_activity,
            "is_pinned": is_pinned
        })

    print(f"✓ Created {len(topics)} discussion topics")

    # ========================================================================
    # STEP 10: Create Development Phases
    # ========================================================================
    print("\nStep 10: Creating 4 development phases...")

    phases = [
        ('Phase 1 - The Pines (Complete)', '[{"lot_number":"1-001","status":"sold","sqft":10500}]', 'https://thehighlands.com/maps/phase1.pdf'),
        ('Phase 2 - The Preserve (Active)', '[{"lot_number":"2-002","status":"available","sqft":15500,"price":185000}]', 'https://thehighlands.com/maps/phase2.pdf'),
        ('Phase 3 - Lakeside Village (Coming Soon)', '[{"lot_number":"3-001","status":"coming_soon","sqft":12000}]', 'https://thehighlands.com/maps/phase3.pdf'),
        ('Fairway Pines - 55+ Active Adult', '[{"lot_number":"FP-001","status":"available","sqft":8500,"price":145000}]', 'https://thehighlands.com/maps/fairway-pines.pdf')
    ]

    for name, lots, map_url in phases:
        conn.execute(text("""
            INSERT INTO community_phases (community_id, name, lots, map_url)
            VALUES (:community_id, :name, :lots, :map_url)
            ON DUPLICATE KEY UPDATE name=name
        """), {
            "community_id": community_id,
            "name": name,
            "lots": lots,
            "map_url": map_url
        })

    print(f"✓ Created {len(phases)} development phases")

    # ========================================================================
    # STEP 11: Create Community Admin Profile
    # ========================================================================
    print("\nStep 11: Creating Fred Caldwell's admin profile...")

    # Check if profile already exists
    profile_check = conn.execute(text("""
        SELECT id FROM community_admin_profiles WHERE user_id = :user_id
    """), {"user_id": user_id})

    if profile_check.fetchone():
        print("✓ Admin profile already exists")
    else:
        conn.execute(text("""
            INSERT INTO community_admin_profiles (
                user_id, community_id, first_name, last_name, profile_image, bio, title,
                contact_email, contact_phone, contact_preferred,
                can_post_announcements, can_manage_events, can_moderate_threads
            ) VALUES (
                :user_id, :community_id, 'Fred', 'Caldwell',
                'https://caldwellcos.com/wp-content/uploads/fred-caldwell-headshot.jpg',
                'Fred Caldwell is the President and CEO of Caldwell Communities, bringing over 30 years of experience in creating award-winning master-planned communities across the Greater Houston area. Under his visionary leadership, Caldwell Communities has developed more than 10 successful communities and earned the prestigious Greater Houston Builders Association Developer of the Year Award in 2024, 2023, and 2019.

The Highlands represents the pinnacle of Fred''s commitment to creating communities that harmonize with nature while providing world-class amenities and exceptional quality of life. His passion for environmental stewardship is evident in The Highlands'' 200-acre nature preserve, 30+ miles of trails, and careful preservation of the area''s natural beauty.',
                'President & CEO, Caldwell Communities',
                'fred.caldwell@caldwellcos.com', '(281) 765-9900', 'email',
                1, 1, 1
            )
        """), {"user_id": user_id, "community_id": community_id})

        print("✓ Created community admin profile")

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 60)
    print("✅ The Highlands seed data completed successfully!")
    print("=" * 60)

    # Get final counts
    counts = conn.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM community_amenities WHERE community_id = :cid) as amenities,
            (SELECT COUNT(*) FROM community_events WHERE community_id = :cid) as events,
            (SELECT COUNT(*) FROM community_builders WHERE community_id = :cid) as builders,
            (SELECT COUNT(*) FROM community_awards WHERE community_id = :cid) as awards,
            (SELECT COUNT(*) FROM community_topics WHERE community_id = :cid) as topics,
            (SELECT COUNT(*) FROM community_phases WHERE community_id = :cid) as phases
    """), {"cid": community_id})

    counts_row = counts.fetchone()
    print(f"\nCreated records:")
    print(f"  • Amenities: {counts_row[0]}")
    print(f"  • Events: {counts_row[1]}")
    print(f"  • Builders: {counts_row[2]}")
    print(f"  • Awards: {counts_row[3]}")
    print(f"  • Topics: {counts_row[4]}")
    print(f"  • Phases: {counts_row[5]}")
    print(f"\n✓ Fred Caldwell (User ID: {user_id})")
    print(f"✓ The Highlands (Community ID: {community_id})")


def downgrade() -> None:
    """Remove The Highlands seed data"""

    conn = op.get_bind()

    print("Removing The Highlands seed data...")

    # Get the community ID
    comm_result = conn.execute(text("""
        SELECT id FROM communities WHERE name = 'The Highlands' AND city = 'Porter'
    """))
    comm_row = comm_result.fetchone()

    if not comm_row:
        print("✓ The Highlands community not found, nothing to remove")
        return

    community_id = comm_row[0]

    # Get user ID
    user_result = conn.execute(text("""
        SELECT user_id FROM community_admin_profiles WHERE community_id = :community_id
    """), {"community_id": community_id})
    user_row = user_result.fetchone()

    if user_row:
        user_id = user_row[0]

        # Delete admin profile
        conn.execute(text("""
            DELETE FROM community_admin_profiles WHERE user_id = :user_id
        """), {"user_id": user_id})

        # Delete user
        conn.execute(text("""
            DELETE FROM users WHERE id = :user_id
        """), {"user_id": user_id})

    # Delete community (cascade will handle related records)
    conn.execute(text("""
        DELETE FROM communities WHERE id = :community_id
    """), {"community_id": community_id})

    print("✓ Removed The Highlands community and related data")
