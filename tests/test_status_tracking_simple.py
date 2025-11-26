#!/usr/bin/env python3
"""
Test script to verify availability_status change tracking using raw SQL.
"""
from sqlalchemy import text
from config.db import SessionLocal

def test_status_tracking():
    """Test that status tracking fields are properly set."""
    db = SessionLocal()

    try:
        # Query communities with status tracking fields using raw SQL
        query = text("""
            SELECT
                community_id,
                name,
                city,
                state,
                enterprise_number_hoa,
                development_stage,
                development_status,
                availability_status,
                status_changed_at,
                status_change_reason,
                last_activity_at,
                community_dues,
                monthly_fee,
                created_at
            FROM communities
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 5
        """)

        result = db.execute(query, {"user_id": "USR-1763443503-N3UTFX"})
        communities = result.fetchall()

        print("\n" + "="*80)
        print("RECENT COMMUNITIES WITH STATUS TRACKING")
        print("="*80 + "\n")

        if not communities:
            print("⚠️  No communities found with admin user ID")
            return

        for comm in communities:
            print(f"📍 {comm.name}")
            print(f"   ID: {comm.community_id}")
            print(f"   Enterprise #: {comm.enterprise_number_hoa or 'N/A'}")
            print(f"   Location: {comm.city}, {comm.state}")
            print(f"\n   Development:")
            print(f"   - Stage: {comm.development_stage or 'N/A'}")
            print(f"   - Status: {comm.development_status or 'N/A'}")
            print(f"   - Availability: {comm.availability_status or 'N/A'}")
            print(f"\n   Status Tracking:")
            print(f"   - Changed At: {comm.status_changed_at or 'N/A'}")
            print(f"   - Change Reason: {comm.status_change_reason or 'N/A'}")
            print(f"   - Last Activity: {comm.last_activity_at or 'N/A'}")
            print(f"\n   Financials:")
            print(f"   - Community Dues (Yearly): {comm.community_dues or 'N/A'}")
            print(f"   - Monthly Fee: {comm.monthly_fee or 'N/A'}")
            print(f"\n   Created: {comm.created_at}")
            print("\n" + "-"*80 + "\n")

        # Summary
        communities_with_tracking = sum(1 for c in communities if c.status_changed_at)
        communities_with_reason = sum(1 for c in communities if c.status_change_reason)
        communities_with_activity = sum(1 for c in communities if c.last_activity_at)

        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total communities checked: {len(communities)}")
        print(f"✅ With status_changed_at: {communities_with_tracking}")
        print(f"✅ With status_change_reason: {communities_with_reason}")
        print(f"✅ With last_activity_at: {communities_with_activity}")

        if communities_with_tracking == len(communities):
            print("\n🎉 All communities have proper status tracking!")
        else:
            print("\n⚠️  Some communities missing status tracking fields")
            print(f"   Missing tracking: {len(communities) - communities_with_tracking} communities")

    finally:
        db.close()

if __name__ == "__main__":
    test_status_tracking()
