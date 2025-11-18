#!/usr/bin/env python3
"""
Create CommunityAdminProfile for user USR-1763002155-GRZVLL
Links the user to The Highlands community
"""

import sys
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, ".")

from config.db import SessionLocal
from model.user import Users
from model.profiles.community_admin_profile import CommunityAdminProfile
from model.profiles.community import Community
from model.profiles.buyer import BuyerProfile
from model.profiles.builder import BuilderProfile
from src.id_generator import generate_community_admin_id


def create_admin_profile():
    """Create community admin profile for user USR-1763002155-GRZVLL"""
    db: Session = SessionLocal()

    try:
        # Step 1: Find the user
        user_id = "USR-1763002155-GRZVLL"
        user = db.query(Users).filter(Users.user_id == user_id).first()

        if not user:
            print(f"❌ User {user_id} not found")
            return

        print(f"✅ Found user: {user.first_name} {user.last_name} (ID: {user.id})")

        # Step 2: Find The Highlands community
        community = db.query(Community).filter(
            Community.name == "The Highlands"
        ).first()

        if not community:
            print("❌ The Highlands community not found")
            print("Trying to find community by ID 3...")
            community = db.query(Community).filter(Community.id == 3).first()

        if not community:
            print("❌ Community not found")
            return

        print(f"✅ Found community: {community.name} (ID: {community.id})")

        # Step 3: Check if profile already exists
        existing = db.query(CommunityAdminProfile).filter(
            CommunityAdminProfile.user_id == user.user_id
        ).first()

        if existing:
            print(f"⚠️  Community admin profile already exists for this user")
            print(f"   Profile ID: {existing.id}")
            print(f"   Community ID: {existing.community_id}")
            print(f"   Community Admin ID: {existing.community_admin_id}")
            return

        # Step 4: Create new community admin profile
        print("\n📝 Creating community admin profile...")

        community_admin_id = generate_community_admin_id()

        profile = CommunityAdminProfile(
            community_admin_id=community_admin_id,
            user_id=user.user_id,
            community_id=community.id,
            first_name=user.first_name,
            last_name=user.last_name,
            # Optional fields
            profile_image=None,
            bio=None,
            title="Community Admin",
            contact_email=user.email,
            contact_phone=user.phone_e164,
            contact_preferred="email",
            # Permissions (defaults to True)
            can_post_announcements=True,
            can_manage_events=True,
            can_moderate_threads=True,
            extra=None
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

        print(f"✅ Created community admin profile:")
        print(f"   ID: {profile.id}")
        print(f"   Community Admin ID: {profile.community_admin_id}")
        print(f"   User: {profile.first_name} {profile.last_name} ({profile.user_id})")
        print(f"   Community: {community.name} (ID: {profile.community_id})")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_profile()
