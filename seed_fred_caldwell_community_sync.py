#!/usr/bin/env python3
"""
Seed script for Fred Caldwell's Community Profile (Synchronous version)
Creates a complete community with all related data
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import select

# Import all models to resolve SQLAlchemy relationships
from model.base import Base  # Import first
from model.user import Users, Role
from model.profiles.buyer import BuyerProfile  # Import to resolve Users relationships
from model.profiles.builder import BuilderProfile  # Import to resolve Users relationships
from model.profiles.community import (
    Community,
    CommunityAmenity,
    CommunityEvent,
    CommunityBuilder,
    CommunityAdmin,
    CommunityAward,
    CommunityTopic,
    CommunityPhase,
)
from model.profiles.community_admin_profile import CommunityAdminProfile
from config.db import SessionLocal


def create_fred_caldwell_community():
    """Create Fred Caldwell's community profile with all related data"""

    # Get database session
    db = SessionLocal()

    try:
        # ================================================================
        # STEP 1: Create or find Fred Caldwell user
        # ================================================================
        print("Step 1: Creating/finding Fred Caldwell user...")

        # Check if Fred Caldwell already exists
        fred_user = db.query(Users).filter(
            (Users.first_name == "Fred") & (Users.last_name == "Caldwell")
        ).first()

        if fred_user:
            print(f"✓ Found existing user: Fred Caldwell (ID: {fred_user.id})")
        else:
            # Get community admin role
            admin_role = db.query(Role).filter(Role.key == "community_admin").first()

            if not admin_role:
                print("✗ Community admin role not found. Creating default role...")
                admin_role = Role(
                    key="community_admin",
                    name="Community Admin",
                    description="Community administrator role"
                )
                db.add(admin_role)
                db.flush()

            # Create Fred Caldwell user
            fred_user = Users(
                public_id=str(uuid.uuid4()),
                email="fred.caldwell@oakmeadows.org",
                first_name="Fred",
                last_name="Caldwell",
                phone_e164="+15125550199",
                role=admin_role.key,  # Direct role string instead of FK
                onboarding_completed=True,
                is_email_verified=True,
                plan_tier="pro",
                status="active"
            )
            db.add(fred_user)
            db.flush()
            print(f"✓ Created user: Fred Caldwell (ID: {fred_user.id})")

        # ================================================================
        # STEP 2: Create Oak Meadows Community
        # ================================================================
        print("\nStep 2: Creating Oak Meadows community...")

        # Check if community already exists for this user
        existing_admin_profile = db.query(CommunityAdminProfile).filter(
            CommunityAdminProfile.user_id == fred_user.id
        ).first()

        if existing_admin_profile:
            print(f"✓ User already has community admin profile (Community ID: {existing_admin_profile.community_id})")
            community = db.query(Community).filter(Community.id == existing_admin_profile.community_id).first()
            print(f"✓ Using existing community: {community.name}")
        else:
            # Create new community
            community = Community(
                public_id=f"oak-meadows-{str(uuid.uuid4())[:8]}",
                name="Oak Meadows",
                city="Austin",
                state="TX",
                postal_code="78704",
                community_dues="$500/year",
                tax_rate="2.1%",
                monthly_fee="$125/month",
                followers=1247,
                about="""Oak Meadows is a vibrant, family-friendly master-planned community nestled in the heart of Austin, Texas. Featuring resort-style amenities, award-winning schools, and a strong sense of community, Oak Meadows offers residents an exceptional lifestyle with easy access to downtown Austin, major employers, and outdoor recreation.

Our community is home to 524 families and continues to grow with new phases under development. We pride ourselves on maintaining beautiful common spaces, hosting engaging community events, and fostering neighborly connections.""",
                is_verified=True,
                homes=524,
                residents=1847,
                founded_year=2018,
                member_count=1247,
                development_stage="Phase 3",
                enterprise_number_hoa="HOA-TX-2018-0524",
                intro_video_url="https://youtube.com/watch?v=oak-meadows-intro",
                community_website_url="https://oakmeadows.org"
            )
            db.add(community)
            db.flush()
            print(f"✓ Created community: {community.name} (ID: {community.id})")

        # ================================================================
        # STEP 3: Create amenities
        # ================================================================
        print("\nStep 3: Creating community amenities...")

        amenities_data = [
            {
                "name": "Resort-Style Pool",
                "gallery": [
                    "https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7",
                    "https://images.unsplash.com/photo-1575429198097-0414ec08e8cd"
                ]
            },
            {
                "name": "State-of-the-Art Fitness Center",
                "gallery": [
                    "https://images.unsplash.com/photo-1534438327276-14e5300c3a48"
                ]
            },
            {
                "name": "Walking & Biking Trails",
                "gallery": [
                    "https://images.unsplash.com/photo-1551632811-561732d1e306"
                ]
            },
            {
                "name": "Dog Park",
                "gallery": [
                    "https://images.unsplash.com/photo-1548199973-03cce0bbc87b"
                ]
            },
            {
                "name": "Playground & Splash Pad",
                "gallery": [
                    "https://images.unsplash.com/photo-1578683010236-d716f9a3f461"
                ]
            },
            {
                "name": "Community Clubhouse",
                "gallery": [
                    "https://images.unsplash.com/photo-1582407947304-fd86f028f716"
                ]
            }
        ]

        for amenity_data in amenities_data:
            amenity = CommunityAmenity(
                community_id=community.id,
                name=amenity_data["name"],
                gallery=amenity_data["gallery"]
            )
            db.add(amenity)

        db.flush()
        print(f"✓ Created {len(amenities_data)} amenities")

        # ================================================================
        # STEP 4: Create upcoming events
        # ================================================================
        print("\nStep 4: Creating community events...")

        now = datetime.utcnow()
        events_data = [
            {
                "title": "Annual Summer BBQ & Pool Party",
                "description": "Join your neighbors for our annual summer celebration! Free food, music, and fun for the whole family.",
                "location": "Community Pool & Clubhouse",
                "start_at": now + timedelta(days=15),
                "end_at": now + timedelta(days=15, hours=4),
                "is_public": True
            },
            {
                "title": "HOA Board Meeting",
                "description": "Monthly board meeting to discuss community matters. All residents welcome.",
                "location": "Community Clubhouse - Conference Room",
                "start_at": now + timedelta(days=7),
                "end_at": now + timedelta(days=7, hours=2),
                "is_public": True
            },
            {
                "title": "Kids Movie Night Under the Stars",
                "description": "Family-friendly movie screening on the lawn. Bring blankets and chairs!",
                "location": "Community Green Space",
                "start_at": now + timedelta(days=22),
                "end_at": now + timedelta(days=22, hours=3),
                "is_public": True
            },
            {
                "title": "Fitness Bootcamp",
                "description": "Free fitness class led by certified trainer. All fitness levels welcome!",
                "location": "Fitness Center",
                "start_at": now + timedelta(days=3),
                "end_at": now + timedelta(days=3, hours=1),
                "is_public": True
            }
        ]

        for event_data in events_data:
            event = CommunityEvent(
                community_id=community.id,
                **event_data
            )
            db.add(event)

        db.flush()
        print(f"✓ Created {len(events_data)} events")

        # ================================================================
        # STEP 5: Create builder cards
        # ================================================================
        print("\nStep 5: Creating builder cards...")

        builders_data = [
            {
                "icon": "building.2.fill",
                "name": "Taylor Morrison",
                "subtitle": "Luxury Custom Homes",
                "followers": 1542,
                "is_verified": True
            },
            {
                "icon": "house.fill",
                "name": "Lennar Homes",
                "subtitle": "Energy-Efficient Living",
                "followers": 2341,
                "is_verified": True
            },
            {
                "icon": "building.fill",
                "name": "David Weekley Homes",
                "subtitle": "Award-Winning Builder",
                "followers": 987,
                "is_verified": True
            }
        ]

        for builder_data in builders_data:
            builder = CommunityBuilder(
                community_id=community.id,
                **builder_data
            )
            db.add(builder)

        db.flush()
        print(f"✓ Created {len(builders_data)} builder cards")

        # ================================================================
        # STEP 6: Create community admins (contact info)
        # ================================================================
        print("\nStep 6: Creating community admin contacts...")

        admins_data = [
            {
                "name": "Fred Caldwell",
                "role": "HOA President",
                "email": "fred.caldwell@oakmeadows.org",
                "phone": "(512) 555-0199"
            },
            {
                "name": "Sarah Martinez",
                "role": "Vice President",
                "email": "sarah.martinez@oakmeadows.org",
                "phone": "(512) 555-0156"
            },
            {
                "name": "Michael Chen",
                "role": "Treasurer",
                "email": "michael.chen@oakmeadows.org",
                "phone": "(512) 555-0178"
            }
        ]

        for admin_data in admins_data:
            admin = CommunityAdmin(
                community_id=community.id,
                **admin_data
            )
            db.add(admin)

        db.flush()
        print(f"✓ Created {len(admins_data)} admin contacts")

        # ================================================================
        # STEP 7: Create community awards
        # ================================================================
        print("\nStep 7: Creating community awards...")

        awards_data = [
            {
                "title": "Best Master-Planned Community",
                "year": 2023,
                "issuer": "Austin Home Builders Association",
                "icon": "rosette",
                "note": "Recognized for outstanding community design and amenities"
            },
            {
                "title": "Community of the Year",
                "year": 2022,
                "issuer": "Texas HOA Management",
                "icon": "star.fill",
                "note": "Awarded for exceptional community engagement and management"
            },
            {
                "title": "Green Community Award",
                "year": 2024,
                "issuer": "Austin Environmental Council",
                "icon": "leaf.fill",
                "note": "For sustainable practices and environmental stewardship"
            }
        ]

        for award_data in awards_data:
            award = CommunityAward(
                community_id=community.id,
                **award_data
            )
            db.add(award)

        db.flush()
        print(f"✓ Created {len(awards_data)} awards")

        # ================================================================
        # STEP 8: Create discussion topics
        # ================================================================
        print("\nStep 8: Creating discussion topics...")

        topics_data = [
            {
                "title": "Pool Hours Extension Request",
                "category": "Amenities",
                "replies": 24,
                "last_activity": "2 hours ago",
                "is_pinned": True,
                "comments": [
                    {
                        "author": "Jennifer Smith",
                        "text": "Would love to see pool hours extended to 10pm in summer!",
                        "timestamp": "2024-11-10T14:30:00Z"
                    },
                    {
                        "author": "Fred Caldwell",
                        "text": "We're discussing this at the next board meeting. Thanks for the feedback!",
                        "timestamp": "2024-11-10T16:45:00Z"
                    }
                ]
            },
            {
                "title": "New Playground Equipment Ideas",
                "category": "General",
                "replies": 15,
                "last_activity": "1 day ago",
                "is_pinned": False,
                "comments": []
            },
            {
                "title": "Landscaping Maintenance Schedule",
                "category": "Maintenance",
                "replies": 8,
                "last_activity": "3 days ago",
                "is_pinned": True,
                "comments": []
            }
        ]

        for topic_data in topics_data:
            topic = CommunityTopic(
                community_id=community.id,
                **topic_data
            )
            db.add(topic)

        db.flush()
        print(f"✓ Created {len(topics_data)} discussion topics")

        # ================================================================
        # STEP 9: Create development phases
        # ================================================================
        print("\nStep 9: Creating development phases...")

        phases_data = [
            {
                "name": "Phase 1 - Established",
                "lots": [
                    {"lot_number": "1-001", "status": "sold", "sqft": 8500, "price": None},
                    {"lot_number": "1-002", "status": "sold", "sqft": 9200, "price": None},
                    {"lot_number": "1-003", "status": "sold", "sqft": 8800, "price": None}
                ],
                "map_url": "https://oakmeadows.org/maps/phase1.pdf"
            },
            {
                "name": "Phase 2 - Nearly Complete",
                "lots": [
                    {"lot_number": "2-001", "status": "sold", "sqft": 10000, "price": None},
                    {"lot_number": "2-002", "status": "available", "sqft": 11500, "price": 145000}
                ],
                "map_url": "https://oakmeadows.org/maps/phase2.pdf"
            },
            {
                "name": "Phase 3 - Under Development",
                "lots": [
                    {"lot_number": "3-001", "status": "available", "sqft": 12000, "price": 165000},
                    {"lot_number": "3-002", "status": "available", "sqft": 11000, "price": 155000},
                    {"lot_number": "3-003", "status": "available", "sqft": 13500, "price": 185000}
                ],
                "map_url": "https://oakmeadows.org/maps/phase3.pdf"
            }
        ]

        for phase_data in phases_data:
            phase = CommunityPhase(
                community_id=community.id,
                **phase_data
            )
            db.add(phase)

        db.flush()
        print(f"✓ Created {len(phases_data)} development phases")

        # ================================================================
        # STEP 10: Create Community Admin Profile for Fred Caldwell
        # ================================================================
        if not existing_admin_profile:
            print("\nStep 10: Creating Fred Caldwell's admin profile...")

            admin_profile = CommunityAdminProfile(
                user_id=fred_user.id,
                community_id=community.id,
                first_name="Fred",
                last_name="Caldwell",
                profile_image="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e",
                bio="""Fred Caldwell has served as HOA President of Oak Meadows since 2020. With over 15 years of experience in community management and a passion for creating exceptional living environments, Fred leads our community with dedication and vision.

Under Fred's leadership, Oak Meadows has received multiple awards for community excellence and has seen significant improvements in amenities and resident satisfaction. Fred is committed to transparency, fiscal responsibility, and fostering a strong sense of community among all residents.""",
                title="HOA President",
                contact_email="fred.caldwell@oakmeadows.org",
                contact_phone="(512) 555-0199",
                contact_preferred="email",
                can_post_announcements=True,
                can_manage_events=True,
                can_moderate_threads=True
            )
            db.add(admin_profile)
            db.flush()
            print(f"✓ Created community admin profile for Fred Caldwell")
        else:
            print("\nStep 10: Fred Caldwell already has admin profile - skipping")

        # ================================================================
        # COMMIT ALL CHANGES
        # ================================================================
        db.commit()

        print("\n" + "="*60)
        print("✅ Successfully created Fred Caldwell's community profile!")
        print("="*60)
        print(f"\nUser ID: {fred_user.id}")
        print(f"User Public ID: {fred_user.public_id}")
        print(f"Community ID: {community.id}")
        print(f"Community Public ID: {community.public_id}")
        print(f"Community Name: {community.name}")
        print(f"\nYou can now access Fred Caldwell's community profile in the iOS app!")

        return {
            "user_id": fred_user.id,
            "user_public_id": fred_user.public_id,
            "community_id": community.id,
            "community_public_id": community.public_id,
            "community_name": community.name
        }

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating community profile: {str(e)}")
        raise
    finally:
        db.close()


def main():
    """Main entry point"""
    print("="*60)
    print("Fred Caldwell Community Profile Seed Script")
    print("="*60)
    print()

    try:
        result = create_fred_caldwell_community()
        print(f"\n✅ Script completed successfully!")
        print(f"Community Public ID: {result['community_public_id']}")
        return result
    except Exception as e:
        print(f"\n❌ Script failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = main()
