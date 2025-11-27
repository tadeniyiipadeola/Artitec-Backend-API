"""
Simple script to:
1. Delete all properties via direct SQL
2. Fetch all builders from database
3. Create property inventory collection jobs for each builder
"""
import sys
import requests
from sqlalchemy import text
from config.db import SessionLocal


BASE_URL = 'http://127.0.0.1:8000'


def clear_all_properties_sql():
    """Delete all properties using raw SQL."""
    print("=" * 80)
    print("STEP 1: Clearing all existing properties...")
    print("=" * 80)

    db = SessionLocal()
    try:
        # Count existing properties
        result = db.execute(text("SELECT COUNT(*) FROM properties"))
        count = result.scalar()
        print(f"\n📊 Found {count} existing properties in database")

        if count == 0:
            print("✅ No properties to delete")
            return 0

        # Ask for confirmation
        response = input(f"\n⚠️  Are you sure you want to DELETE ALL {count} properties? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled")
            sys.exit(0)

        # Delete all properties
        db.execute(text("DELETE FROM properties"))
        db.commit()
        print(f"\n✅ Successfully deleted {count} properties")
        return count

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error deleting properties: {e}")
        raise
    finally:
        db.close()


def get_all_builder_community_pairs():
    """Fetch all active builders and communities, create all combinations."""
    print("\n" + "=" * 80)
    print("STEP 2: Fetching all builders and communities from database...")
    print("=" * 80)

    db = SessionLocal()
    try:
        # Fetch all active builders
        builders_result = db.execute(text("SELECT id, name FROM builder_profiles WHERE is_active = 1"))
        builders = [{'id': row[0], 'name': row[1]} for row in builders_result.fetchall()]

        # Fetch all active communities
        communities_result = db.execute(text("SELECT id, name FROM communities WHERE is_active = 1 LIMIT 5"))
        communities = [{'id': row[0], 'name': row[1]} for row in communities_result.fetchall()]

        print(f"\n📊 Found {len(builders)} active builders")
        print(f"📊 Found {len(communities)} active communities (limited to 5 for testing)")

        # Create all combinations of builder x community
        pairs = []
        for builder in builders:
            for community in communities:
                pairs.append({
                    'builder_id': builder['id'],
                    'builder_name': builder['name'],
                    'community_id': community['id'],
                    'community_name': community['name']
                })

        print(f"📊 Created {len(pairs)} builder-community pairs")

        if pairs:
            print("\n📋 Sample builder-community pairs:")
            for idx, pair in enumerate(pairs[:10], 1):  # Show first 10
                print(f"  {idx}. {pair['builder_name']} @ {pair['community_name']} (Builder: {pair['builder_id']}, Community: {pair['community_id']})")
            if len(pairs) > 10:
                print(f"  ... and {len(pairs) - 10} more")

        return pairs

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db.close()


def create_property_inventory_jobs(pairs):
    """Create property inventory collection jobs for each builder-community pair."""
    print("\n" + "=" * 80)
    print("STEP 3: Creating property inventory jobs for all builder-community pairs...")
    print("=" * 80)

    created_jobs = []
    failed_jobs = []

    for idx, pair in enumerate(pairs, 1):
        builder_id = pair.get('builder_id')
        community_id = pair.get('community_id')
        builder_name = pair.get('builder_name', 'Unknown')
        community_name = pair.get('community_name', 'Unknown')

        print(f"\n[{idx}/{len(pairs)}] Creating job for: {builder_name} @ {community_name}")

        try:
            # Create property inventory job with both builder_id and community_id
            response = requests.post(
                f'{BASE_URL}/v1/admin/collection/jobs',
                json={
                    'entity_type': 'property',
                    'entity_id': community_id,
                    'job_type': 'inventory',
                    'priority': 5,
                    'builder_id': builder_id,
                    'community_id': community_id
                },
                timeout=10
            )

            if response.status_code == 200:
                job = response.json()
                created_jobs.append(job)
                print(f"  ✅ Created job: {job['job_id']}")
            else:
                failed_jobs.append({
                    'pair': f"{builder_name} @ {community_name}",
                    'error': f"HTTP {response.status_code}: {response.text[:100]}"
                })
                print(f"  ❌ Failed: HTTP {response.status_code}")

        except Exception as e:
            failed_jobs.append({
                'pair': f"{builder_name} @ {community_name}",
                'error': str(e)
            })
            print(f"  ❌ Error: {e}")

    return created_jobs, failed_jobs


def start_all_jobs(jobs):
    """Start all created jobs."""
    print("\n" + "=" * 80)
    print("STEP 4: Starting all created jobs...")
    print("=" * 80)

    started_jobs = []
    failed_starts = []

    for idx, job in enumerate(jobs, 1):
        job_id = job['job_id']
        print(f"\n[{idx}/{len(jobs)}] Starting job: {job_id}")

        try:
            response = requests.post(
                f'{BASE_URL}/v1/admin/collection/jobs/{job_id}/start',
                timeout=10
            )

            if response.status_code == 200:
                started_jobs.append(job_id)
                print(f"  ✅ Started successfully")
            else:
                failed_starts.append({
                    'job_id': job_id,
                    'error': f"HTTP {response.status_code}"
                })
                print(f"  ❌ Failed: HTTP {response.status_code}")

        except Exception as e:
            failed_starts.append({
                'job_id': job_id,
                'error': str(e)
            })
            print(f"  ❌ Error: {e}")

    return started_jobs, failed_starts


def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("PROPERTY CLEANUP AND BUILDER DATA COLLECTION")
    print("=" * 80)

    try:
        # Step 1: Clear all properties
        deleted_count = clear_all_properties_sql()

        # Step 2: Get all builder-community pairs
        pairs = get_all_builder_community_pairs()

        if not pairs:
            print("\n⚠️  No builder-community pairs found. Exiting.")
            return

        # Step 3: Create collection jobs
        created_jobs, failed_job_creation = create_property_inventory_jobs(pairs)

        # Step 4: Start all jobs
        if created_jobs:
            response = input(f"\n🚀 Start all {len(created_jobs)} jobs now? (yes/no): ")
            if response.lower() == 'yes':
                started_jobs, failed_starts = start_all_jobs(created_jobs)
            else:
                print("\n⏸️  Jobs created but not started. You can start them manually.")
                started_jobs = []
                failed_starts = []
        else:
            started_jobs = []
            failed_starts = []

        # Final summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print(f"\n📊 Properties deleted: {deleted_count}")
        print(f"📊 Builder-community pairs found: {len(pairs)}")
        print(f"✅ Jobs created: {len(created_jobs)}")
        print(f"❌ Job creation failures: {len(failed_job_creation)}")
        print(f"🚀 Jobs started: {len(started_jobs)}")
        print(f"⚠️  Start failures: {len(failed_starts)}")

        if failed_job_creation:
            print("\n❌ Failed job creations:")
            for fail in failed_job_creation:
                print(f"  - {fail['pair']}: {fail['error']}")

        if failed_starts:
            print("\n⚠️  Failed to start:")
            for fail in failed_starts:
                print(f"  - {fail['job_id']}: {fail['error']}")

        if created_jobs:
            print("\n📋 Created Job IDs:")
            for job in created_jobs[:10]:  # Show first 10
                print(f"  - {job['job_id']}")
            if len(created_jobs) > 10:
                print(f"  ... and {len(created_jobs) - 10} more")

        print("\n✅ Process completed!")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
