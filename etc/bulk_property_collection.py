"""
Bulk Property Inventory Collection Script

This script creates property inventory collection jobs for all builder-community
associations in your database. This will populate the properties table with
listings from all your builders.

Usage:
    python bulk_property_collection.py [--priority PRIORITY] [--limit LIMIT] [--dry-run]

Options:
    --priority PRIORITY   Job priority (1-10), default: 5
    --limit LIMIT        Limit number of jobs to create (for testing)
    --dry-run            Show what would be created without creating jobs
    --auto-start         Automatically start jobs after creating them
"""

import os
import sys
import argparse
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DB_URL = os.getenv("DB_URL")


def get_builder_community_pairs(limit=None):
    """
    Get all builder-community pairs from the database.

    Returns:
        List of tuples: (builder_id, builder_name, community_id, community_name, location)
    """
    engine = create_engine(DB_URL)

    query = '''
        SELECT
            bp.id as builder_id,
            bp.name as builder_name,
            c.id as community_id,
            c.name as community_name,
            c.city,
            c.state
        FROM builder_communities bc
        JOIN builder_profiles bp ON bc.builder_id = bp.id
        JOIN communities c ON bc.community_id = c.id
        ORDER BY bp.name, c.name
    '''

    if limit:
        query += f' LIMIT {limit}'

    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [(row[0], row[1], row[2], row[3], f"{row[4]}, {row[5]}") for row in result]


def create_property_inventory_job(builder_id, community_id, builder_name, community_name, location, priority=5):
    """
    Create a property inventory collection job via API.

    Args:
        builder_id: Builder ID
        community_id: Community ID
        builder_name: Builder name
        community_name: Community name
        location: Location string (city, state)
        priority: Job priority (1-10)

    Returns:
        dict: API response with job details or None if failed
    """
    url = f"{API_BASE_URL}/v1/admin/collection/jobs"

    payload = {
        "entity_type": "property",
        "job_type": "inventory",
        "search_query": "",  # Not used for property inventory
        "priority": priority,
        "builder_id": builder_id,
        "community_id": community_id,
        "location": location
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ❌ API Error: {e}")
        return None


def start_job(job_id):
    """Start a collection job."""
    url = f"{API_BASE_URL}/v1/admin/collection/jobs/{job_id}/start"
    try:
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Failed to start job: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Bulk create property inventory collection jobs")
    parser.add_argument("--priority", type=int, default=5, help="Job priority (1-10)")
    parser.add_argument("--limit", type=int, help="Limit number of jobs to create")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without creating")
    parser.add_argument("--auto-start", action="store_true", help="Automatically start jobs after creation")

    args = parser.parse_args()

    # Validate priority
    if not 1 <= args.priority <= 10:
        print("❌ Priority must be between 1 and 10")
        sys.exit(1)

    print("=" * 80)
    print("BULK PROPERTY INVENTORY COLLECTION")
    print("=" * 80)
    print()

    # Get builder-community pairs
    print("📊 Fetching builder-community associations from database...")
    pairs = get_builder_community_pairs(args.limit)

    if not pairs:
        print("❌ No builder-community associations found in database")
        print()
        print("💡 You need to first run builder or community discovery jobs to")
        print("   establish which builders build in which communities.")
        sys.exit(1)

    print(f"✅ Found {len(pairs)} builder-community pairs")
    print()

    if args.dry_run:
        print("🔍 DRY RUN MODE - No jobs will be created")
        print()
        print("The following jobs would be created:")
        print("-" * 80)
        for i, (builder_id, builder_name, community_id, community_name, location) in enumerate(pairs, 1):
            print(f"{i}. {builder_name} @ {community_name} ({location})")
            print(f"   Builder ID: {builder_id}, Community ID: {community_id}, Priority: {args.priority}")
        print()
        print(f"Total: {len(pairs)} property inventory jobs would be created")
        return

    # Confirm before proceeding
    print(f"⚠️  This will create {len(pairs)} property inventory collection jobs")
    print(f"   Priority: {args.priority}")
    print(f"   Auto-start: {'Yes' if args.auto_start else 'No'}")
    print()

    response = input("Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        return

    print()
    print("🚀 Creating property inventory jobs...")
    print("=" * 80)

    created = []
    failed = []

    for i, (builder_id, builder_name, community_id, community_name, location) in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}] {builder_name} @ {community_name}")
        print(f"         Location: {location}")
        print(f"         Builder ID: {builder_id}, Community ID: {community_id}")

        # Create job
        job = create_property_inventory_job(
            builder_id, community_id, builder_name,
            community_name, location, args.priority
        )

        if job:
            job_id = job.get('job_id')
            print(f"  ✅ Created job: {job_id}")
            created.append((job_id, builder_name, community_name))

            # Auto-start if requested
            if args.auto_start:
                if start_job(job_id):
                    print(f"  ✅ Started job")
                else:
                    print(f"  ⚠️  Job created but failed to start")
        else:
            failed.append((builder_name, community_name))

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully created: {len(created)} jobs")
    print(f"❌ Failed: {len(failed)} jobs")

    if created and not args.auto_start:
        print()
        print("💡 Jobs created but not started. You can:")
        print("   1. Start individual jobs via the admin UI")
        print("   2. Start all pending jobs via: /v1/admin/collection/jobs/execute-pending")
        print("   3. Re-run this script with --auto-start flag")

    if failed:
        print()
        print("Failed jobs:")
        for builder_name, community_name in failed:
            print(f"  - {builder_name} @ {community_name}")


if __name__ == "__main__":
    main()
