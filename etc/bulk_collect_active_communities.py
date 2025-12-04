#!/usr/bin/env python3
"""
Bulk Collection Script for Active Communities

This script creates collection jobs for builders and properties
for all communities where development_stage is NOT 'Completed'.

It will:
1. Find all active communities (not completed)
2. Create builder collection jobs for each community
3. Create property inventory collection jobs for each community
4. Execute jobs in batches to avoid overwhelming the system
"""
import sys
import time
import requests
from sqlalchemy import text
from config.db import SessionLocal

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000/v1/admin/collection"

def get_active_communities():
    """Get all communities that are not completed."""
    db = SessionLocal()
    try:
        query = text("""
            SELECT
                id,
                community_id,
                name,
                city,
                state,
                development_stage,
                development_status,
                availability_status
            FROM communities
            WHERE development_stage != 'Completed'
               OR development_stage IS NULL
            ORDER BY created_at DESC
        """)

        result = db.execute(query)
        communities = result.fetchall()
        return communities
    finally:
        db.close()

def create_builder_job(community_id, community_name, location):
    """Create a builder collection job for a community."""
    try:
        payload = {
            "entity_type": "builder",
            "job_type": "discovery",
            "entity_id": None,
            "search_query": f"home builders in {community_name}",
            "location": location,
            "community_id": community_id,
            "priority": 5
        }

        response = requests.post(
            f"{API_BASE_URL}/jobs",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            job_data = response.json()
            return job_data.get("job_id")
        else:
            print(f"   ❌ Failed to create builder job: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Error creating builder job: {e}")
        return None

def create_property_job(community_id, community_name, location):
    """Create a property inventory collection job for a community."""
    try:
        payload = {
            "entity_type": "property",
            "job_type": "inventory",
            "entity_id": None,
            "search_query": f"homes for sale in {community_name}",
            "location": location,
            "community_id": community_id,
            "priority": 5
        }

        response = requests.post(
            f"{API_BASE_URL}/jobs",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            job_data = response.json()
            return job_data.get("job_id")
        else:
            print(f"   ❌ Failed to create property job: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Error creating property job: {e}")
        return None

def execute_pending_jobs(limit=5):
    """Execute pending jobs."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/jobs/execute",
            params={"limit": limit},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("executed_count", 0)
        else:
            print(f"   ❌ Failed to execute jobs: {response.status_code}")
            return 0
    except Exception as e:
        print(f"   ❌ Error executing jobs: {e}")
        return 0

def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("BULK COLLECTION FOR ACTIVE COMMUNITIES")
    print("="*80 + "\n")

    # Step 1: Get active communities
    print("📋 Fetching active communities (not completed)...\n")
    communities = get_active_communities()

    if not communities:
        print("⚠️  No active communities found.")
        return

    print(f"✅ Found {len(communities)} active communities\n")
    print("-"*80 + "\n")

    # Step 2: Create jobs for each community
    builder_jobs = []
    property_jobs = []

    for idx, comm in enumerate(communities, 1):
        location = f"{comm.city}, {comm.state}" if comm.city and comm.state else comm.state or comm.city

        print(f"[{idx}/{len(communities)}] {comm.name}")
        print(f"   Location: {location}")
        print(f"   Stage: {comm.development_stage or 'N/A'}")
        print(f"   Status: {comm.development_status}")

        # Create builder job
        print(f"   🏗️  Creating builder collection job...")
        builder_job_id = create_builder_job(comm.id, comm.name, location)
        if builder_job_id:
            builder_jobs.append(builder_job_id)
            print(f"   ✅ Builder job created: {builder_job_id}")

        # Create property job
        print(f"   🏘️  Creating property collection job...")
        property_job_id = create_property_job(comm.id, comm.name, location)
        if property_job_id:
            property_jobs.append(property_job_id)
            print(f"   ✅ Property job created: {property_job_id}")

        print()

        # Small delay to avoid overwhelming the API
        time.sleep(0.5)

    # Step 3: Summary
    print("\n" + "="*80)
    print("JOB CREATION SUMMARY")
    print("="*80)
    print(f"Total communities processed: {len(communities)}")
    print(f"Builder jobs created: {len(builder_jobs)}")
    print(f"Property jobs created: {len(property_jobs)}")
    print(f"Total jobs created: {len(builder_jobs) + len(property_jobs)}")

    # Step 4: Ask to execute jobs
    print("\n" + "-"*80)
    print("EXECUTION OPTIONS")
    print("-"*80)
    print("\nJobs have been created but not executed yet.")
    print("You can execute them in batches to control system load.\n")

    response = input("Do you want to execute jobs now? (yes/no): ").lower()

    if response in ['yes', 'y']:
        batch_size = int(input("\nHow many jobs to execute at once? (default: 5): ") or "5")

        print(f"\n🚀 Executing jobs in batches of {batch_size}...")

        total_jobs = len(builder_jobs) + len(property_jobs)
        executed = 0

        while executed < total_jobs:
            count = execute_pending_jobs(batch_size)
            if count > 0:
                executed += count
                print(f"   ✅ Executed {count} jobs ({executed}/{total_jobs} total)")
                time.sleep(2)  # Wait between batches
            else:
                break

        print(f"\n✅ Execution complete: {executed} jobs executed")
    else:
        print("\nℹ️  Jobs created but not executed.")
        print("   You can execute them later via:")
        print(f"   POST {API_BASE_URL}/jobs/execute?limit=5")

    print("\n" + "="*80)
    print("COMPLETED")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
