"""
Test the new parallel processing system.

This script:
1. Creates a community discovery job for an area with multiple communities
2. Starts the job (which will create community records + builder jobs)
3. Starts the concurrent executor to process builder jobs in parallel
4. Monitors progress
"""

import time
import requests
import argparse
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/v1/admin/collection"


def create_test_job(location: str):
    """Create a community discovery job."""
    print(f"\n{'='*80}")
    print(f"Creating community discovery job for: {location}")
    print('='*80)

    response = requests.post(
        f"{BASE_URL}/jobs",
        json={
            "entity_type": "community",
            "job_type": "discovery",
            "search_query": location,
            "location": location,
            "priority": 8
        }
    )

    if response.status_code == 200:
        job = response.json()
        job_id = job['job_id']
        print(f"✅ Created job: {job_id}")
        return job_id
    else:
        print(f"❌ Failed to create job: {response.status_code}")
        print(response.text)
        return None


def start_job(job_id: str):
    """Start the community discovery job."""
    print(f"\n{'='*80}")
    print(f"Starting job: {job_id}")
    print('='*80)

    response = requests.post(f"{BASE_URL}/jobs/{job_id}/start")

    if response.status_code == 200:
        print(f"✅ Job started successfully")
        return True
    else:
        print(f"❌ Failed to start job: {response.status_code}")
        print(response.text)
        return False


def get_job_status(job_id: str):
    """Get job status."""
    response = requests.get(f"{BASE_URL}/jobs/{job_id}")

    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_job_logs(job_id: str, limit: int = 50):
    """Get job logs."""
    response = requests.get(f"{BASE_URL}/jobs/{job_id}/logs?limit={limit}")

    if response.status_code == 200:
        return response.json()['logs']
    else:
        return []


def get_pending_jobs_by_type():
    """Get count of pending jobs by entity type."""
    counts = {}

    for entity_type in ['community', 'builder', 'property', 'sales_rep']:
        response = requests.get(
            f"{BASE_URL}/jobs?entity_type={entity_type}&status=pending"
        )

        if response.status_code == 200:
            data = response.json()
            counts[entity_type] = data['total_jobs']

    return counts


def get_running_jobs_by_type():
    """Get count of running jobs by entity type."""
    counts = {}

    for entity_type in ['community', 'builder', 'property', 'sales_rep']:
        response = requests.get(
            f"{BASE_URL}/jobs?entity_type={entity_type}&status=running"
        )

        if response.status_code == 200:
            data = response.json()
            counts[entity_type] = data['total_jobs']

    return counts


def monitor_job(job_id: str, max_wait: int = 300):
    """Monitor job until completion or timeout."""
    print(f"\n{'='*80}")
    print(f"Monitoring job: {job_id}")
    print('='*80)

    start_time = time.time()
    last_status = None

    while time.time() - start_time < max_wait:
        job = get_job_status(job_id)

        if not job:
            print(f"❌ Job not found")
            return False

        status = job['status']
        items_found = job.get('items_found', 0)
        new_entities = job.get('new_entities_found', 0)
        changes = job.get('changes_detected', 0)

        if status != last_status:
            print(f"\n📊 Status: {status}")
            print(f"   Items Found: {items_found}")
            print(f"   New Entities: {new_entities}")
            print(f"   Changes Detected: {changes}")
            last_status = status

        if status == "completed":
            print(f"\n✅ Job completed successfully!")
            print(f"   Total Items: {items_found}")
            print(f"   New Entities: {new_entities}")
            print(f"   Changes: {changes}")

            # Show recent logs
            logs = get_job_logs(job_id, limit=10)
            if logs:
                print(f"\n📝 Recent logs:")
                for log in logs[-5:]:
                    print(f"   [{log['level']}] {log['message']}")

            return True

        elif status == "failed":
            error = job.get('error_message', 'Unknown error')
            print(f"\n❌ Job failed: {error}")

            # Show error logs
            logs = get_job_logs(job_id, limit=20)
            if logs:
                print(f"\n📝 Error logs:")
                for log in logs[-10:]:
                    if log['level'] in ['ERROR', 'WARNING']:
                        print(f"   [{log['level']}] {log['message']}")

            return False

        time.sleep(2)

    print(f"\n⏱️ Timeout after {max_wait} seconds")
    return False


def monitor_system(duration: int = 120):
    """Monitor the overall system progress."""
    print(f"\n{'='*80}")
    print(f"Monitoring system for {duration} seconds")
    print('='*80)

    start_time = time.time()

    while time.time() - start_time < duration:
        pending = get_pending_jobs_by_type()
        running = get_running_jobs_by_type()

        print(f"\n📊 System Status [{int(time.time() - start_time)}s]")
        print(f"   Pending: Community={pending.get('community', 0)}, "
              f"Builder={pending.get('builder', 0)}, "
              f"Property={pending.get('property', 0)}, "
              f"SalesRep={pending.get('sales_rep', 0)}")
        print(f"   Running: Community={running.get('community', 0)}, "
              f"Builder={running.get('builder', 0)}, "
              f"Property={running.get('property', 0)}, "
              f"SalesRep={running.get('sales_rep', 0)}")

        # Check if there are no more pending or running jobs
        total_pending = sum(pending.values())
        total_running = sum(running.values())

        if total_pending == 0 and total_running == 0:
            print(f"\n✅ All jobs completed!")
            return True

        time.sleep(5)

    print(f"\n⏱️ Monitoring period ended")
    return False


def main():
    """Run the test."""
    parser = argparse.ArgumentParser(description='Test the parallel processing system')
    parser.add_argument(
        '--location',
        type=str,
        default='Frisco, TX',
        help='Location to search for communities'
    )
    parser.add_argument(
        '--monitor-duration',
        type=int,
        default=120,
        help='How long to monitor system progress (seconds)'
    )
    parser.add_argument(
        '--skip-community-job',
        action='store_true',
        help='Skip creating community job (useful if testing with existing jobs)'
    )

    args = parser.parse_args()

    print(f"\n{'#'*80}")
    print(f"# Parallel Processing System Test")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# Location: {args.location}")
    print(f"{'#'*80}")

    community_job_id = None

    if not args.skip_community_job:
        # Step 1: Create and start community discovery job
        community_job_id = create_test_job(args.location)
        if not community_job_id:
            print(f"\n❌ Test failed: Could not create community job")
            return

        # Step 2: Start the community job
        if not start_job(community_job_id):
            print(f"\n❌ Test failed: Could not start community job")
            return

        # Step 3: Monitor community job until completion
        print(f"\n{'='*80}")
        print(f"Phase 1: Community Discovery")
        print('='*80)

        if not monitor_job(community_job_id, max_wait=600):
            print(f"\n❌ Test failed: Community job did not complete successfully")
            return

        # Wait a bit for builder jobs to be created
        print(f"\n⏳ Waiting 5 seconds for builder jobs to be created...")
        time.sleep(5)

    # Step 4: Check how many builder jobs were created
    pending = get_pending_jobs_by_type()
    builder_jobs = pending.get('builder', 0)

    print(f"\n{'='*80}")
    print(f"Phase 2: Builder Discovery (Parallel Processing)")
    print('='*80)
    print(f"📊 Found {builder_jobs} pending builder jobs")

    if builder_jobs == 0:
        print(f"\n⚠️  No builder jobs found to process")
        if community_job_id:
            print(f"   Community job: {community_job_id}")
        return

    print(f"\n🚀 Start the executor in another terminal:")
    print(f"   python run_executor.py --iterations 50 --poll-interval 5")
    print(f"\n   Or let it run automatically if already started")

    # Step 5: Monitor overall system progress
    if monitor_system(duration=args.monitor_duration):
        print(f"\n✅ Test completed successfully!")
        print(f"\n📊 Final Results:")

        # Get final job counts
        final_pending = get_pending_jobs_by_type()
        final_running = get_running_jobs_by_type()

        print(f"   Pending: {sum(final_pending.values())} total")
        print(f"   Running: {sum(final_running.values())} total")

        # Get completed jobs
        for entity_type in ['community', 'builder', 'property']:
            response = requests.get(
                f"{BASE_URL}/jobs?entity_type={entity_type}&status=completed"
            )
            if response.status_code == 200:
                count = response.json()['total_jobs']
                print(f"   Completed {entity_type}: {count}")

    else:
        print(f"\n⏱️ Test monitoring period ended")
        print(f"   Jobs may still be processing")

    print(f"\n{'#'*80}")
    print(f"# Test Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}")


if __name__ == "__main__":
    main()
