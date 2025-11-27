"""
Script to:
1. Clear all existing properties from the database
2. Fetch all builders from the database
3. Create property inventory collection jobs for each builder
"""
import asyncio
import sys
from sqlalchemy.orm import Session
from config.db import SessionLocal
from model.property.property import Property
from model.profiles.builder import BuilderProfile
import requests

BASE_URL = 'http://127.0.0.1:8000'


def clear_all_properties(db: Session):
    """Delete all properties from the database."""
    print("=" * 80)
    print("STEP 1: Clearing all existing properties...")
    print("=" * 80)

    # Count existing properties
    count = db.query(Property).count()
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
    try:
        deleted = db.query(Property).delete()
        db.commit()
        print(f"\n✅ Successfully deleted {deleted} properties")
        return deleted
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error deleting properties: {e}")
        raise


def get_all_builders(db: Session):
    """Fetch all builders from the database."""
    print("\n" + "=" * 80)
    print("STEP 2: Fetching all builders from database...")
    print("=" * 80)

    builders = db.query(BuilderProfile).filter(
        BuilderProfile.status == 'active'
    ).all()

    print(f"\n📊 Found {len(builders)} active builders")

    if builders:
        print("\n📋 Builders:")
        for idx, builder in enumerate(builders, 1):
            print(f"  {idx}. {builder.company_name} (ID: {builder.id})")

    return builders


def create_property_inventory_jobs(builders):
    """Create property inventory collection jobs for each builder."""
    print("\n" + "=" * 80)
    print("STEP 3: Creating property inventory jobs for all builders...")
    print("=" * 80)

    created_jobs = []
    failed_jobs = []

    for idx, builder in enumerate(builders, 1):
        print(f"\n[{idx}/{len(builders)}] Creating job for: {builder.company_name}")

        try:
            # Create property inventory job
            response = requests.post(
                f'{BASE_URL}/v1/admin/collection/jobs',
                json={
                    'entity_type': 'property',
                    'entity_id': builder.id,
                    'job_type': 'inventory',
                    'priority': 5,
                    'builder_id': builder.id
                },
                timeout=10
            )

            if response.status_code == 200:
                job = response.json()
                created_jobs.append(job)
                print(f"  ✅ Created job: {job['job_id']}")
            else:
                failed_jobs.append({
                    'builder': builder.company_name,
                    'error': f"HTTP {response.status_code}: {response.text}"
                })
                print(f"  ❌ Failed: HTTP {response.status_code}")

        except Exception as e:
            failed_jobs.append({
                'builder': builder.company_name,
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

    # Get database session
    db = SessionLocal()

    try:
        # Step 1: Clear all properties
        deleted_count = clear_all_properties(db)

        # Step 2: Get all builders
        builders = get_all_builders(db)

        if not builders:
            print("\n⚠️  No active builders found. Exiting.")
            return

        # Step 3: Create collection jobs
        created_jobs, failed_job_creation = create_property_inventory_jobs(builders)

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
        print(f"📊 Builders found: {len(builders)}")
        print(f"✅ Jobs created: {len(created_jobs)}")
        print(f"❌ Job creation failures: {len(failed_job_creation)}")
        print(f"🚀 Jobs started: {len(started_jobs)}")
        print(f"⚠️  Start failures: {len(failed_starts)}")

        if failed_job_creation:
            print("\n❌ Failed job creations:")
            for fail in failed_job_creation:
                print(f"  - {fail['builder']}: {fail['error']}")

        if failed_starts:
            print("\n⚠️  Failed to start:")
            for fail in failed_starts:
                print(f"  - {fail['job_id']}: {fail['error']}")

        if created_jobs:
            print("\n📋 Created Job IDs:")
            for job in created_jobs:
                print(f"  - {job['job_id']}")

        print("\n✅ Process completed!")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
