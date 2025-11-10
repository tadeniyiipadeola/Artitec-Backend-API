#!/usr/bin/env python3
"""
Create a COMPLETE community profile with ALL data for testing CommunityView.
This populates the communities table and all related tables.

Usage:
    python scripts/create_full_community_profile.py
"""

import sys
import os
from datetime import datetime, timedelta
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.db import get_db
from model.profiles.community import (
    Community,
    CommunityAmenity,
    CommunityEvent,
    CommunityBuilder,
    CommunityAdmin,
    CommunityAward,
    CommunityTopic,
    CommunityPhase
)


def create_full_community_profile():
    """Create a complete community profile with ALL nested data."""
    db = next(get_db())

    try:
        print("=" * 80)
        print("  Creating FULL Community Profile with ALL Data")
        print("=" * 80)
        print()

        # 1. CREATE MAIN COMMUNITY PROFILE
        print("1️⃣  Creating main community profile...")
        community = Community(
            public_id=str(uuid.uuid4()),
            name="Oak Meadows",
            city="Austin",
            postal_code="78704",

            # Finance
            community_dues="$500/year",
            tax_rate="2.1%",
            monthly_fee="$125",

            # Stats
            followers=1250,
            residents=1847,
            homes=524,
            founded_year=2018,
            member_count=1250,

            # Description
            about=(
                "Oak Meadows is a vibrant, family-friendly community nestled in the heart of Austin, Texas. "
                "With over 500 homes spanning 200 acres, we offer resort-style amenities, excellent schools, "
                "and a strong sense of community. Our tree-lined streets, parks, and walking trails provide "
                "the perfect setting for families to grow and thrive.\n\n"
                "Our community features:\n"
                "• Resort-style pool and fitness center\n"
                "• Walking trails and parks\n"
                "• Community events year-round\n"
                "• Active HOA with dedicated volunteers\n"
                "• Close to top-rated schools\n"
                "• Minutes from downtown Austin"
            ),

            # Media
            intro_video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",

            # Verification
            is_verified=True
        )
        db.add(community)
        db.flush()  # Get the ID

        print(f"   ✓ Created: {community.name}")
        print(f"   ✓ ID: {community.id}")
        print(f"   ✓ Public ID: {community.public_id}")

        # 2. ADD AMENITIES
        print("\n2️⃣  Adding amenities...")
        amenities_data = [
            {
                "name": "Resort-Style Pool & Hot Tub",
                "gallery": [
                    "/uploads/amenities/pool1.jpg",
                    "/uploads/amenities/pool2.jpg",
                    "/uploads/amenities/pool3.jpg",
                    "/uploads/amenities/hottub1.jpg"
                ]
            },
            {
                "name": "State-of-the-Art Fitness Center",
                "gallery": [
                    "/uploads/amenities/gym1.jpg",
                    "/uploads/amenities/gym2.jpg",
                    "/uploads/amenities/gym3.jpg"
                ]
            },
            {
                "name": "Community Clubhouse & Event Space",
                "gallery": [
                    "/uploads/amenities/clubhouse1.jpg",
                    "/uploads/amenities/clubhouse2.jpg",
                    "/uploads/amenities/clubhouse_kitchen.jpg"
                ]
            },
            {
                "name": "Nature Trails & Walking Paths",
                "gallery": [
                    "/uploads/amenities/trails1.jpg",
                    "/uploads/amenities/trails2.jpg",
                    "/uploads/amenities/trails_sunset.jpg"
                ]
            },
            {
                "name": "Playground & Splash Pad",
                "gallery": [
                    "/uploads/amenities/playground1.jpg",
                    "/uploads/amenities/splashpad1.jpg",
                    "/uploads/amenities/playground2.jpg"
                ]
            },
            {
                "name": "Dog Park",
                "gallery": [
                    "/uploads/amenities/dogpark1.jpg",
                    "/uploads/amenities/dogpark2.jpg"
                ]
            },
            {
                "name": "Tennis & Pickleball Courts",
                "gallery": [
                    "/uploads/amenities/tennis1.jpg",
                    "/uploads/amenities/pickleball1.jpg"
                ]
            }
        ]

        for amenity_data in amenities_data:
            amenity = CommunityAmenity(
                community_id=community.id,
                **amenity_data
            )
            db.add(amenity)

        print(f"   ✓ Added {len(amenities_data)} amenities")

        # 3. ADD UPCOMING EVENTS
        print("\n3️⃣  Adding community events...")
        events_data = [
            {
                "title": "Summer Pool Party & BBQ",
                "description": "Join us for our annual summer kickoff! Free food, live music, and family fun. Don't miss the pie eating contest!",
                "location": "Main Pool Area",
                "start_at": datetime.now() + timedelta(days=15),
                "end_at": datetime.now() + timedelta(days=15, hours=4),
                "is_public": True
            },
            {
                "title": "HOA Board Meeting",
                "description": "Monthly HOA board meeting. All residents welcome to attend and voice concerns.",
                "location": "Clubhouse Conference Room",
                "start_at": datetime.now() + timedelta(days=7),
                "end_at": datetime.now() + timedelta(days=7, hours=2),
                "is_public": True
            },
            {
                "title": "Kids Movie Night Under the Stars",
                "description": "Family-friendly movie screening with popcorn and snacks. Bring your blankets and lawn chairs!",
                "location": "Community Park Lawn",
                "start_at": datetime.now() + timedelta(days=20),
                "end_at": datetime.now() + timedelta(days=20, hours=3),
                "is_public": True
            },
            {
                "title": "Neighborhood Garage Sale",
                "description": "Community-wide garage sale. Sign up to participate or just come browse!",
                "location": "Throughout Community",
                "start_at": datetime.now() + timedelta(days=30),
                "end_at": datetime.now() + timedelta(days=30, hours=6),
                "is_public": True
            },
            {
                "title": "Fitness Bootcamp Series",
                "description": "Free 6-week fitness bootcamp led by certified trainer. All fitness levels welcome!",
                "location": "Fitness Center",
                "start_at": datetime.now() + timedelta(days=10),
                "end_at": datetime.now() + timedelta(days=10, hours=1),
                "is_public": True
            }
        ]

        for event_data in events_data:
            event = CommunityEvent(
                community_id=community.id,
                **event_data
            )
            db.add(event)

        print(f"   ✓ Added {len(events_data)} upcoming events")

        # 4. ADD BUILDER CARDS (Builders working in this community)
        print("\n4️⃣  Adding builder cards...")
        builders_data = [
            {
                "icon": "building.2",
                "name": "Heritage Homes",
                "subtitle": "Custom luxury builders since 1995",
                "followers": 3420,
                "is_verified": True
            },
            {
                "icon": "house.fill",
                "name": "Austin Dream Builders",
                "subtitle": "Energy-efficient modern homes",
                "followers": 2150,
                "is_verified": True
            },
            {
                "icon": "building.columns",
                "name": "Texas Premier Homes",
                "subtitle": "Award-winning craftmanship",
                "followers": 1890,
                "is_verified": True
            }
        ]

        for builder_data in builders_data:
            builder = CommunityBuilder(
                community_id=community.id,
                **builder_data
            )
            db.add(builder)

        print(f"   ✓ Added {len(builders_data)} builder cards")

        # 5. ADD COMMUNITY ADMINS (Contact info)
        print("\n5️⃣  Adding community administrators...")
        admins_data = [
            {
                "name": "Sarah Johnson",
                "role": "HOA President",
                "email": "sarah.johnson@oakmeadows.org",
                "phone": "(512) 555-0123"
            },
            {
                "name": "Michael Chen",
                "role": "Property Manager",
                "email": "michael.chen@oakmeadows.org",
                "phone": "(512) 555-0124"
            },
            {
                "name": "Jennifer Martinez",
                "role": "Events Coordinator",
                "email": "jennifer.martinez@oakmeadows.org",
                "phone": "(512) 555-0125"
            }
        ]

        for admin_data in admins_data:
            admin = CommunityAdmin(
                community_id=community.id,
                **admin_data
            )
            db.add(admin)

        print(f"   ✓ Added {len(admins_data)} community administrators")

        # 6. ADD AWARDS
        print("\n6️⃣  Adding community awards...")
        awards_data = [
            {
                "title": "Best Master-Planned Community",
                "year": 2023,
                "issuer": "Austin Home Builders Association",
                "icon": "rosette",
                "note": "Awarded for outstanding community design, amenities, and resident satisfaction"
            },
            {
                "title": "Green Community Award",
                "year": 2022,
                "issuer": "Texas Environmental Council",
                "icon": "leaf.fill",
                "note": "Recognized for sustainable practices, conservation efforts, and eco-friendly initiatives"
            },
            {
                "title": "Community of the Year",
                "year": 2021,
                "issuer": "Austin Monthly Magazine",
                "icon": "star.fill",
                "note": "Top-rated community for family-friendliness and quality of life"
            }
        ]

        for award_data in awards_data:
            award = CommunityAward(
                community_id=community.id,
                **award_data
            )
            db.add(award)

        print(f"   ✓ Added {len(awards_data)} awards")

        # 7. ADD DISCUSSION THREADS/TOPICS
        print("\n7️⃣  Adding discussion threads...")
        threads_data = [
            {
                "title": "🎉 Pool Hours Extended for Summer!",
                "category": "Announcements",
                "replies": 23,
                "last_activity": "2 hours ago",
                "is_pinned": True,
                "comments": [
                    {
                        "author": "Sarah Johnson",
                        "text": "Great news! Starting June 1st, pool hours extended to 9pm on weekdays and 10pm on weekends.",
                        "timestamp": "2024-05-25T10:00:00"
                    }
                ]
            },
            {
                "title": "Recommendations for landscaping companies?",
                "category": "Home & Garden",
                "replies": 15,
                "last_activity": "1 day ago",
                "is_pinned": False,
                "comments": []
            },
            {
                "title": "⚠️ Speed limit enforcement on Oak Drive",
                "category": "Safety",
                "replies": 45,
                "last_activity": "3 hours ago",
                "is_pinned": True,
                "comments": []
            },
            {
                "title": "New playground equipment installed!",
                "category": "Announcements",
                "replies": 12,
                "last_activity": "5 hours ago",
                "is_pinned": False,
                "comments": []
            },
            {
                "title": "Lost dog - Golden Retriever",
                "category": "Pets",
                "replies": 8,
                "last_activity": "1 hour ago",
                "is_pinned": False,
                "comments": []
            },
            {
                "title": "Best pizza delivery?",
                "category": "Recommendations",
                "replies": 34,
                "last_activity": "6 hours ago",
                "is_pinned": False,
                "comments": []
            }
        ]

        for thread_data in threads_data:
            thread = CommunityTopic(
                community_id=community.id,
                **thread_data
            )
            db.add(thread)

        print(f"   ✓ Added {len(threads_data)} discussion threads")

        # 8. ADD DEVELOPMENT PHASES (with lots info)
        print("\n8️⃣  Adding development phases...")
        phases_data = [
            {
                "name": "Phase 1 - The Oaks",
                "lots": [
                    {"lot_number": "101", "status": "sold", "sqft": 3200, "price": 425000},
                    {"lot_number": "102", "status": "sold", "sqft": 2850, "price": 395000},
                    {"lot_number": "103", "status": "available", "sqft": 3100, "price": 415000},
                    {"lot_number": "104", "status": "sold", "sqft": 3500, "price": 475000},
                    {"lot_number": "105", "status": "sold", "sqft": 2900, "price": 405000}
                ],
                "map_url": "/uploads/phases/phase1-map.pdf"
            },
            {
                "name": "Phase 2 - Meadow View",
                "lots": [
                    {"lot_number": "201", "status": "sold", "sqft": 3500, "price": 485000},
                    {"lot_number": "202", "status": "reserved", "sqft": 3300, "price": 455000},
                    {"lot_number": "203", "status": "available", "sqft": 3800, "price": 525000},
                    {"lot_number": "204", "status": "sold", "sqft": 3200, "price": 445000}
                ],
                "map_url": "/uploads/phases/phase2-map.pdf"
            },
            {
                "name": "Phase 3 - Sunset Hills",
                "lots": [
                    {"lot_number": "301", "status": "available", "sqft": 4000, "price": 565000},
                    {"lot_number": "302", "status": "available", "sqft": 3750, "price": 535000},
                    {"lot_number": "303", "status": "reserved", "sqft": 3900, "price": 555000}
                ],
                "map_url": "/uploads/phases/phase3-map.pdf"
            }
        ]

        for phase_data in phases_data:
            phase = CommunityPhase(
                community_id=community.id,
                **phase_data
            )
            db.add(phase)

        print(f"   ✓ Added {len(phases_data)} development phases")

        # COMMIT ALL CHANGES
        print("\n💾 Committing all data to database...")
        db.commit()

        print("\n" + "=" * 80)
        print("  ✅ SUCCESS! Complete Community Profile Created")
        print("=" * 80)
        print(f"\n📊 Summary:")
        print(f"   Community Name: {community.name}")
        print(f"   Community ID: {community.id}")
        print(f"   Public ID: {community.public_id}")
        print(f"\n📦 Data Created:")
        print(f"   ├─ {len(amenities_data)} Amenities")
        print(f"   ├─ {len(events_data)} Events")
        print(f"   ├─ {len(builders_data)} Builder Cards")
        print(f"   ├─ {len(admins_data)} Administrators")
        print(f"   ├─ {len(awards_data)} Awards")
        print(f"   ├─ {len(threads_data)} Discussion Threads")
        print(f"   └─ {len(phases_data)} Development Phases")
        print(f"\n🚀 Next Steps:")
        print(f"   1. Link a user to this community:")
        print(f"      python scripts/create_community_admin_sample.py --user-id <USER_ID> --community-id {community.id}")
        print(f"\n   2. Update CommunityDashboard.swift:")
        print(f"      userCommunityId = {community.id}")
        print(f"\n   3. Test the API:")
        print(f"      curl http://127.0.0.1:8000/v1/profiles/communities/{community.id}?include=amenities,events,builder_cards,admins,awards,threads,phases")
        print(f"\n   4. Launch iOS app and navigate to Community profile!")
        print()

        return community.id

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating community profile: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    print()
    community_id = create_full_community_profile()

    if community_id:
        sys.exit(0)
    else:
        print("\n❌ FAILED - Check error messages above")
        sys.exit(1)
