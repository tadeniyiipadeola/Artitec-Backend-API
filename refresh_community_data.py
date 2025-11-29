#!/usr/bin/env python3
"""
Refresh Community Data Script
==============================
This script creates "refresh" collection jobs for all existing communities
to populate the newly added fields (phone, email, sales_office_address, schools, etc.)
that were previously being collected but not stored.

Usage:
    python refresh_community_data.py [--limit N] [--dry-run]

Options:
    --limit N    Only refresh the first N communities (for testing)
    --dry-run    Show what would be done without creating jobs
    --monitor    Monitor job progress after creation
"""

import requests
import sys
import time
import argparse
from typing import List, Dict

BASE_URL = 'http://127.0.0.1:8000'
API_BASE = f'{BASE_URL}/v1/admin/collection'


def get_all_communities() -> List[Dict]:
    """Fetch all communities from the database."""
    print("Fetching existing communities...")

    # Query the communities endpoint
    # Note: Adjust this endpoint based on your actual API structure
    response = requests.get(f'{BASE_URL}/v1/communities', params={'limit': 1000})

    if response.status_code != 200:
        print(f"❌ Failed to fetch communities: {response.status_code}")
        print(response.text)
        return []

    communities = response.json()

    # Handle different response formats
    if isinstance(communities, dict):
        if 'items' in communities:
            communities = communities['items']
        elif 'communities' in communities:
            communities = communities['communities']

    print(f"✅ Found {len(communities)} communities")
    return communities


def create_refresh_job(community_id: str, community_name: str, dry_run: bool = False) -> Dict:
    """Create a refresh job for a specific community."""

    job_data = {
        'entity_type': 'community',
        'job_type': 'refresh',
        'target_id': community_id,  # The community_id string (e.g., CMY-xxx)
        'priority': 5,  # Medium priority
        'metadata': {
            'reason': 'populate_missing_fields',
            'fields': ['phone', 'email', 'sales_office_address', 'elementary_school',
                      'middle_school', 'high_school', 'developer_name', 'rating', 'review_count']
        }
    }

    if dry_run:
        print(f"  [DRY RUN] Would create refresh job for: {community_name} ({community_id})")
        return {'job_id': 'DRY-RUN', 'status': 'pending'}

    response = requests.post(f'{API_BASE}/jobs', json=job_data)

    if response.status_code == 200:
        job = response.json()
        print(f"  ✅ Created job {job['job_id']} for: {community_name}")
        return job
    else:
        print(f"  ❌ Failed to create job for {community_name}: {response.status_code}")
        print(f"     {response.text}")
        return None


def start_job(job_id: str) -> bool:
    """Start a collection job."""
    response = requests.post(f'{API_BASE}/jobs/{job_id}/start')

    if response.status_code == 200:
        return True
    else:
        print(f"  ❌ Failed to start job {job_id}: {response.status_code}")
        return False


def monitor_jobs(job_ids: List[str], check_interval: int = 10, max_duration: int = 300):
    """Monitor the progress of multiple jobs."""
    print(f"\n{'='*80}")
    print(f"Monitoring {len(job_ids)} jobs (checking every {check_interval}s, max {max_duration}s)")
    print(f"{'='*80}\n")

    start_time = time.time()
    completed = set()
    failed = set()

    while len(completed) + len(failed) < len(job_ids):
        elapsed = time.time() - start_time

        if elapsed > max_duration:
            print(f"\n⏱️  Max monitoring duration ({max_duration}s) reached")
            break

        for job_id in job_ids:
            if job_id in completed or job_id in failed or job_id == 'DRY-RUN':
                continue

            response = requests.get(f'{API_BASE}/jobs/{job_id}')

            if response.status_code == 200:
                job = response.json()
                status = job['status']

                if status == 'completed':
                    completed.add(job_id)
                    changes = job.get('changes_detected', 0)
                    applied = job.get('changes_applied', 0)
                    print(f"✅ {job_id}: COMPLETED - {applied}/{changes} changes applied")

                elif status == 'failed':
                    failed.add(job_id)
                    error = job.get('error_message', 'Unknown error')
                    print(f"❌ {job_id}: FAILED - {error}")

        if len(completed) + len(failed) < len(job_ids):
            remaining = len(job_ids) - len(completed) - len(failed)
            print(f"\r[{int(elapsed)}s] Running: {remaining}, Completed: {len(completed)}, Failed: {len(failed)}", end='', flush=True)
            time.sleep(check_interval)

    print(f"\n\n{'='*80}")
    print(f"Final Summary:")
    print(f"  ✅ Completed: {len(completed)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"  ⏳ Still Running: {len(job_ids) - len(completed) - len(failed)}")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Refresh community data to populate missing fields')
    parser.add_argument('--limit', type=int, help='Only refresh first N communities')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without creating jobs')
    parser.add_argument('--monitor', action='store_true', help='Monitor job progress after creation')
    parser.add_argument('--monitor-duration', type=int, default=300, help='Max monitoring duration in seconds')

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print("Community Data Refresh Script")
    print(f"{'='*80}\n")

    # Fetch communities
    communities = get_all_communities()

    if not communities:
        print("❌ No communities found or failed to fetch")
        return 1

    # Apply limit if specified
    if args.limit:
        communities = communities[:args.limit]
        print(f"Limiting to first {args.limit} communities\n")

    # Create refresh jobs
    print(f"\n{'='*80}")
    print(f"Creating Refresh Jobs{'  (DRY RUN)' if args.dry_run else ''}")
    print(f"{'='*80}\n")

    job_ids = []

    for idx, community in enumerate(communities, 1):
        # Extract community ID and name
        community_id = community.get('community_id') or community.get('id')
        community_name = community.get('name', 'Unknown')

        print(f"[{idx}/{len(communities)}] {community_name} ({community_id})")

        job = create_refresh_job(community_id, community_name, dry_run=args.dry_run)

        if job and job.get('job_id'):
            job_ids.append(job['job_id'])

            # Start the job immediately
            if not args.dry_run:
                if start_job(job['job_id']):
                    print(f"  ▶️  Job started")
                else:
                    print(f"  ⏸️  Job created but not started")

        # Small delay to avoid overwhelming the API
        if not args.dry_run:
            time.sleep(0.5)

    print(f"\n{'='*80}")
    print(f"Summary: Created {len(job_ids)} jobs")
    print(f"{'='*80}\n")

    if args.dry_run:
        print("This was a dry run. Use without --dry-run to actually create jobs.\n")
        return 0

    # Monitor jobs if requested
    if args.monitor and job_ids:
        monitor_jobs(job_ids, max_duration=args.monitor_duration)
    else:
        print("Jobs are running in the background.")
        print(f"Monitor progress at: {BASE_URL}/docs")
        print(f"\nOr run with --monitor to track progress\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
