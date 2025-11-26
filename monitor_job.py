#!/usr/bin/env python3
"""
Monitor a collection job in real-time
"""
import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def get_running_jobs():
    """Get all currently running jobs"""
    try:
        response = requests.get(f"{BASE_URL}/v1/admin/collection/jobs?status=running", timeout=5)
        if response.status_code == 200:
            return response.json().get('jobs', [])
    except:
        pass
    return []

def get_job_details(job_id):
    """Get job details"""
    try:
        response = requests.get(f"{BASE_URL}/v1/admin/collection/jobs/{job_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def get_job_logs(job_id):
    """Get job logs"""
    try:
        response = requests.get(f"{BASE_URL}/v1/admin/collection/jobs/{job_id}/logs", timeout=5)
        if response.status_code == 200:
            return response.json().get('logs', [])
    except:
        pass
    return []

def format_job_info(job):
    """Format job information"""
    print("\n" + "=" * 80)
    print(f"Job ID: {job['job_id']}")
    print(f"Status: {job['status']}")
    print(f"Type: {job['entity_type']} / {job['job_type']}")
    print(f"Progress: Items={job['items_found']}, Entities={job['new_entities_found']}, Changes={job['changes_detected']}")
    print(f"Started: {job.get('started_at', 'N/A')}")
    if job.get('error_message'):
        print(f"❌ Error: {job['error_message']}")
    print("=" * 80)

def main():
    print("🔍 Collection Job Monitor")
    print("Looking for running jobs...")

    # Find running job
    running = get_running_jobs()

    if not running:
        print("\n❌ No jobs currently running.")
        print("\nTo start a job:")
        print("  POST http://127.0.0.1:8000/v1/admin/collection/jobs/execute-pending")
        return

    job_id = running[0]['job_id']
    print(f"\n✅ Found running job: {job_id}")

    # Monitor job
    last_log_count = 0

    while True:
        job = get_job_details(job_id)

        if not job:
            print("\n❌ Job not found (may have been deleted)")
            break

        # Show job info
        format_job_info(job)

        # Get logs
        logs = get_job_logs(job_id)

        # Show new logs
        if len(logs) > last_log_count:
            print("\n📝 Recent Logs:")
            print("-" * 80)
            for log in logs[last_log_count:]:
                level = log.get('level', 'INFO')
                msg = log.get('message', '')
                ts = log.get('timestamp', '')
                print(f"[{level:5s}] {ts} {msg}")
            last_log_count = len(logs)

        # Check if job finished
        if job['status'] not in ['running', 'pending']:
            print(f"\n✅ Job finished with status: {job['status']}")
            if job.get('error_message'):
                print(f"❌ Error: {job['error_message']}")
            break

        # Wait before next check
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")
