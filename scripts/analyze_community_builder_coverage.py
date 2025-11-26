#!/usr/bin/env python3
"""
Analyze Community-Builder Data Coverage

This script analyzes how many communities have builders linked in the database
to identify gaps in the cascading collection workflow (communities → builders → properties).
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func, text
from config.db import get_db

def analyze_coverage():
    """Analyze community-builder data coverage."""

    # Create database session
    db = next(get_db())

    try:
        print("=" * 80)
        print("COMMUNITY-BUILDER DATA COVERAGE ANALYSIS")
        print("=" * 80)
        print()

        # Total communities
        result = db.execute(text("SELECT COUNT(*) FROM communities")).scalar()
        total_communities = result or 0
        print(f"📊 Total Communities: {total_communities}")

        # Communities with builders (via many-to-many relationship)
        result = db.execute(text("""
            SELECT COUNT(DISTINCT community_id)
            FROM builder_communities
        """)).scalar()
        communities_with_builders = result or 0
        print(f"✅ Communities WITH Builders: {communities_with_builders}")

        # Communities without builders
        communities_without_builders = total_communities - communities_with_builders
        print(f"❌ Communities WITHOUT Builders: {communities_without_builders}")

        # Coverage percentage
        coverage_pct = (communities_with_builders / total_communities * 100) if total_communities > 0 else 0
        print(f"📈 Coverage Percentage: {coverage_pct:.1f}%")

        print()

        # Total builder-community associations
        result = db.execute(text("SELECT COUNT(*) FROM builder_communities")).scalar()
        total_associations = result or 0
        print(f"🔗 Total Builder-Community Links: {total_associations}")

        # Average builders per community (for communities that have builders)
        avg_builders = (total_associations / communities_with_builders) if communities_with_builders > 0 else 0
        print(f"📊 Average Builders per Community (with builders): {avg_builders:.2f}")

        print()
        print("=" * 80)
        print("COMMUNITIES WITHOUT BUILDERS (Sample - First 20)")
        print("=" * 80)
        print()

        # Get communities without builders
        result = db.execute(text("""
            SELECT c.id, c.name, c.city, c.state
            FROM communities c
            LEFT JOIN builder_communities bc ON c.id = bc.community_id
            WHERE bc.community_id IS NULL
            LIMIT 20
        """))

        communities_without = result.fetchall()

        if communities_without:
            for i, row in enumerate(communities_without, 1):
                location = f"{row.city}, {row.state}" if row.city and row.state else "Location not specified"
                print(f"{i:2d}. {row.name:40s} | {location:30s} | ID: {row.id}")
        else:
            print("✅ All communities have builders linked!")

        print()
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()

        if communities_without_builders > 0:
            print("⚠️  CRITICAL ISSUE IDENTIFIED:")
            print(f"   {communities_without_builders} communities ({100 - coverage_pct:.1f}%) lack builder data.")
            print()
            print("📋 RECOMMENDED ACTIONS:")
            print()
            print("1. CREATE BACKFILL JOBS:")
            print("   - Create builder discovery jobs for communities without builders")
            print("   - Prioritize master-planned communities and active developments")
            print()
            print("2. IMPROVE COLLECTION WORKFLOW:")
            print("   - When discovering a community, immediately create builder discovery job")
            print("   - Set builder jobs to high priority for communities with properties")
            print()
            print("3. ADD MONITORING:")
            print("   - Track coverage metrics in admin dashboard")
            print("   - Alert when coverage drops below threshold (e.g., 80%)")
            print()
            print("4. MANUAL REVIEW:")
            print("   - Some communities may genuinely have no builders (HOA-only)")
            print("   - Add flag to mark 'builder_data_not_applicable' to skip alerts")
        else:
            print("✅ EXCELLENT: All communities have builder data linked!")
            print("   Continue monitoring to maintain 100% coverage.")

        print()

    finally:
        db.close()

if __name__ == "__main__":
    try:
        analyze_coverage()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
