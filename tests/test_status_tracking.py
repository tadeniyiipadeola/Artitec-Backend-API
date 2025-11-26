#!/usr/bin/env python3
"""
Test script to verify availability_status change tracking.
"""
import sys
from datetime import datetime
from config.db import SessionLocal
from model.profiles.community import Community
from model.user import Users  # Import to avoid SQLAlchemy relationship resolution errors

def test_status_tracking():
    """Test that status tracking fields are properly set."""

    # Create database connection
    db = SessionLocal()

    try:
        # Get most recent communities created by collector
        communities = db.query(Community).filter(
            Community.user_id == "USR-1763443503-N3UTFX"
        ).order_by(Community.created_at.desc()).limit(5).all()

        print("\n" + "="*80)
        print("RECENT COMMUNITIES WITH STATUS TRACKING")
        print("="*80 + "\n")

        if not communities:
            print("⚠️  No communities found with admin user ID")
            return

        for community in communities:
            print(f"📍 {community.name}")
            print(f"   ID: {community.community_id}")
            print(f"   Enterprise #: {community.enterprise_number_hoa or 'N/A'}")
            print(f"   Location: {community.city}, {community.state}")
            print(f"\n   Development:")
            print(f"   - Stage: {community.development_stage or 'N/A'}")
            print(f"   - Status: {community.development_status or 'N/A'}")
            print(f"   - Availability: {community.availability_status or 'N/A'}")
            print(f"\n   Status Tracking:")
            print(f"   - Changed At: {community.status_changed_at or 'N/A'}")
            print(f"   - Change Reason: {community.status_change_reason or 'N/A'}")
            print(f"   - Last Activity: {community.last_activity_at or 'N/A'}")
            print(f"\n   Financials:")
            print(f"   - Community Dues (Yearly): {community.community_dues or 'N/A'}")
            print(f"   - Monthly Fee: {community.monthly_fee or 'N/A'}")
            print(f"\n   Created: {community.created_at}")
            print("\n" + "-"*80 + "\n")

        # Check if fields are properly populated
        communities_with_tracking = [c for c in communities if c.status_changed_at]
        communities_with_reason = [c for c in communities if c.status_change_reason]
        communities_with_activity = [c for c in communities if c.last_activity_at]

        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total communities checked: {len(communities)}")
        print(f"✅ With status_changed_at: {len(communities_with_tracking)}")
        print(f"✅ With status_change_reason: {len(communities_with_reason)}")
        print(f"✅ With last_activity_at: {len(communities_with_activity)}")

        if len(communities_with_tracking) == len(communities):
            print("\n🎉 All communities have proper status tracking!")
        else:
            print("\n⚠️  Some communities missing status tracking fields")

    finally:
        db.close()

if __name__ == "__main__":
    test_status_tracking()
