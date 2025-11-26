#!/usr/bin/env python3
"""
Create a sample community admin profile linking a user to a community.
This allows you to test the CommunityDashboard with real data.

Usage:
    python scripts/create_community_admin_sample.py --user-id 1 --community-id 1
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.db import get_db
from model.profiles.community_admin_profile import CommunityAdminProfile
from model.user import Users
from model.profiles.community import Community


def create_community_admin_profile(user_id: int, community_id: int):
    """Create a community admin profile linking a user to a community"""
    db = next(get_db())

    try:
        print(f"🔍 Checking if user {user_id} exists...")
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            print(f"❌ User with ID {user_id} not found!")
            return False

        print(f"   ✓ Found user: {user.first_name} {user.last_name} ({user.email})")

        print(f"🔍 Checking if community {community_id} exists...")
        community = db.query(Community).filter(Community.id == community_id).first()
        if not community:
            print(f"❌ Community with ID {community_id} not found!")
            return False

        print(f"   ✓ Found community: {community.name}")

        # Check if profile already exists
        existing = db.query(CommunityAdminProfile).filter(
            CommunityAdminProfile.user_id == user_id
        ).first()

        if existing:
            print(f"⚠️  Community admin profile already exists for user {user_id}")
            print(f"   Current community: {existing.community_id}")
            response = input("   Do you want to update it? (y/n): ")
            if response.lower() != 'y':
                print("   Cancelled.")
                return False

            existing.community_id = community_id
            existing.display_name = f"{user.first_name} {user.last_name}"
            existing.title = "Community Administrator"
            existing.contact_email = user.email
            db.add(existing)
            db.commit()
            db.refresh(existing)

            print(f"\n✅ Updated community admin profile!")
            print(f"   Profile ID: {existing.id}")
            print(f"   User: {user.first_name} {user.last_name}")
            print(f"   Community: {community.name}")
            return True

        # Create new profile
        print(f"\n📝 Creating community admin profile...")
        profile = CommunityAdminProfile(
            user_id=user_id,
            community_id=community_id,
            display_name=f"{user.first_name} {user.last_name}",
            title="Community Administrator",
            contact_email=user.email,
            bio=f"Administrator of {community.name}",
            can_post_announcements=True,
            can_manage_events=True,
            can_moderate_threads=True
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

        print(f"\n✅ Successfully created community admin profile!")
        print(f"   Profile ID: {profile.id}")
        print(f"   User: {user.first_name} {user.last_name} (ID: {user_id})")
        print(f"   Community: {community.name} (ID: {community_id})")
        print(f"\n🎯 Next Steps:")
        print(f"   1. Make sure user has role 'community' or 'community_admin'")
        print(f"   2. Sign in as this user in the iOS app")
        print(f"   3. Navigate to the Community profile tab")
        print(f"   4. The app will load community ID {community_id}")

        return True

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create a community admin profile linking a user to a community"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="User ID to make a community admin"
    )
    parser.add_argument(
        "--community-id",
        type=int,
        help="Community ID to assign to this admin"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - prompts for user and community IDs"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  Create Community Admin Profile")
    print("=" * 70)
    print()

    user_id = args.user_id
    community_id = args.community_id

    # Interactive mode
    if args.interactive or (user_id is None and community_id is None):
        try:
            user_id = int(input("Enter User ID: "))
            community_id = int(input("Enter Community ID: "))
        except ValueError:
            print("❌ Invalid input. Please enter numeric IDs.")
            sys.exit(1)

    if user_id is None or community_id is None:
        parser.print_help()
        sys.exit(1)

    success = create_community_admin_profile(user_id, community_id)

    print()
    print("=" * 70)
    if success:
        print("  ✅ SUCCESS!")
    else:
        print("  ❌ FAILED")
    print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
