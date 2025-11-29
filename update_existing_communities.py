#!/usr/bin/env python3
"""
Update Existing Communities Script
===================================
Creates "update" collection jobs for all existing communities to populate
the newly added fields (phone, email, sales_office_address, schools, etc.)

The 'update' job type is designed to refresh data for existing entities.

Usage:
    python update_existing_communities.py [--limit N] [--dry-run] [--monitor]
"""

import requests
import sys
import time
import argparse
from typing import List, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DB_URL = "mysql+pymysql://Dev:Password1!@100.94.199.71:3306/appdb"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

BASE_URL = 'http://127.0.0.1:8000'
API_BASE = f'{BASE_URL}/v1/admin/collection'


def get_all_communities_from_db() -> List[Dict]:
    """Fetch all communities directly from the database."""
    print("Fetching communities from database...")

    db = SessionLocal()
    try:
        query = text("""
            SELECT id, community_id, name, city, state, created_at
            FROM communities
            WHERE is_active = 1
            ORDER BY created_at DESC
        """)

        result = db.execute(query)
        communities = []

        for row in result:
            communities.append({
                'db_id': row[0],  # Numeric ID
                'community_id': row[1],  # String ID (CMY-xxx)
                'name': row[2],
                'city': row[3],
                'state': row[4],
                'created_at': row[5]
            })

        print(f"✅ Found {len(communities)} active communities")
        return communities

    except Exception as e:
        print(f"❌ Error fetching communities: {e}")
        return []
    finally:
        db.close()


def create_update_job(community_db_id: int, community_name: str, dry_run: bool = False) -> Dict:
    """Create an 'update' job for a specific community using the entity_id."""

    job_data = {
        'entity_type': 'community',
        'job_type': 'update',  # Using the update job type for existing entities
        'entity_id': community_db_id,  # The numeric database ID
        'priority': 6  # Medium-high priority
    }

    if dry_run:
        print(f"  [DRY RUN] Would create update job for: {community_name} (ID: {community_db_id})")
        return {'job_id': 'DRY-RUN', 'status': 'pending'}

    try:
        response = requests.post(f'{API_BASE}/jobs', json=job_data, timeout=10)

        if response.status_code == 200:
            job = response.json()
            print(f"  ✅ Job {job['job_id']} created for: {community_name}")
            return job
        else:
            print(f"  ❌ Failed ({response.status_code}) for {community_name}: {response.text[:200]}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed for {community_name}: {e}")
        return None


def start_job(job_id: str) -> bool:
    """Start a collection job."""
    try:
        response = requests.post(f'{API_BASE}/jobs/{job_id}/start', timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"  ❌ Failed to start job {job_id}: {e}")
        return False


def monitor_jobs(job_ids: List[str], check_interval: int = 15, max_duration: int = 600):
    """Monitor the progress of multiple jobs."""
    if not job_ids or 'DRY-RUN' in job_ids:
        return

    print(f"\n{'='*80}")
    print(f"Monitoring {len(job_ids)} jobs (interval: {check_interval}s, max: {max_duration}s)")
    print(f"{'='*80}\n")

    start_time = time.time()
    completed = set()
    failed = set()

    while len(completed) + len(failed) < len(job_ids):
        elapsed = time.time() - start_time

        if elapsed > max_duration:
            print(f"\n⏱️  Max monitoring duration reached ({max_duration}s)")
            break

        for job_id in job_ids:
            if job_id in completed or job_id in failed:
                continue

            try:
                response = requests.get(f'{API_BASE}/jobs/{job_id}', timeout=5)

                if response.status_code == 200:
                    job = response.json()
                    status = job['status']

                    if status == 'completed':
                        completed.add(job_id)
                        changes = job.get('changes_detected', 0)
                        applied = job.get('changes_applied', 0)
                        entity_name = job.get('entity_name', 'Unknown')
                        print(f"✅ {job_id} ({entity_name}): {applied}/{changes} changes applied")

                    elif status == 'failed':
                        failed.add(job_id)
                        error = job.get('error_message', 'Unknown error')
                        print(f"❌ {job_id}: FAILED - {error[:100]}")

            except Exception as e:
                # Just log and continue
                pass

        if len(completed) + len(failed) < len(job_ids):
            remaining = len(job_ids) - len(completed) - len(failed)
            print(f"\r[{int(elapsed)}s] Running: {remaining} | Completed: {len(completed)} | Failed: {len(failed)}", end='', flush=True)
            time.sleep(check_interval)

    print(f"\n\n{'='*80}")
    print("Final Summary:")
    print(f"  ✅ Completed: {len(completed)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"  ⏳ Still Running: {len(job_ids) - len(completed) - len(failed)}")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Update existing communities to populate missing fields')
    parser.add_argument('--limit', type=int, help='Only update first N communities')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without creating jobs')
    parser.add_argument('--monitor', action='store_true', help='Monitor job progress after creation')
    parser.add_argument('--monitor-duration', type=int, default=600, help='Max monitoring duration (default: 600s)')
    parser.add_argument('--batch-delay', type=float, default=1.0, help='Delay between job creations (seconds)')

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print("Update Existing Communities - Populate Missing Fields")
    print(f"{'='*80}\n")

    # Fetch communities from database
    communities = get_all_communities_from_db()

    if not communities:
        print("❌ No communities found")
        return 1

    # Apply limit
    if args.limit:
        communities = communities[:args.limit]
        print(f"Limiting to first {args.limit} communities\n")

    # Create update jobs
    print(f"\n{'='*80}")
    print(f"Creating Update Jobs{'  (DRY RUN)' if args.dry_run else ''}")
    print(f"{'='*80}\n")

    job_ids = []
    for idx, community in enumerate(communities, 1):
        db_id = community['db_id']
        name = community['name']
        location = f"{community.get('city', 'Unknown')}, {community.get('state', '')}"

        print(f"[{idx}/{len(communities)}] {name} ({location})")

        job = create_update_job(db_id, name, dry_run=args.dry_run)

        if job and job.get('job_id'):
            job_id = job['job_id']
            job_ids.append(job_id)

            # Start the job
            if not args.dry_run:
                if start_job(job_id):
                    print(f"  ▶️  Started")
                else:
                    print(f"  ⚠️  Created but failed to start")

            # Delay between jobs to avoid overwhelming the system
            if not args.dry_run and idx < len(communities):
                time.sleep(args.batch_delay)

    print(f"\n{'='*80}")
    print(f"Summary: Created {len(job_ids)} jobs")
    print(f"{'='*80}\n")

    if args.dry_run:
        print("This was a dry run. Remove --dry-run to actually create jobs.\n")
        return 0

    # Monitor if requested
    if args.monitor and job_ids:
        monitor_jobs(job_ids, max_duration=args.monitor_duration)
    else:
        print(f"Jobs are running in background.")
        print(f"Monitor progress: {BASE_URL}/docs\n")
        print(f"Or run with --monitor to track progress here\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
