#!/usr/bin/env python3
"""
Monitor bulk collection jobs progress.

This script monitors the progress of builder and property collection jobs
for active communities.
"""
import sys
import time
import requests
from sqlalchemy import text
from config.db import SessionLocal

API_BASE_URL = "http://127.0.0.1:8000/v1/admin/collection"

def get_job_stats():
    """Get statistics on collection jobs."""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None

def get_recent_jobs(status=None, entity_type=None, limit=50):
    """Get recent jobs filtered by status and entity type."""
    try:
        params = {"page": 1, "page_size": limit}
        if status:
            params["status"] = status
        if entity_type:
            params["entity_type"] = entity_type

        response = requests.get(f"{API_BASE_URL}/jobs", params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("jobs", [])
        return []
    except Exception as e:
        print(f"Error getting jobs: {e}")
        return []

def display_progress():
    """Display collection progress for active communities."""
    print("\n" + "="*80)
    print("BULK COLLECTION PROGRESS MONITOR")
    print("="*80 + "\n")

    # Get overall stats
    stats = get_job_stats()
    if stats:
        print("📊 OVERALL JOB STATISTICS")
        print("-"*80)
        print(f"   Total Jobs: {stats.get('total_jobs', 0)}")
        print(f"   ✅ Completed: {stats.get('completed_jobs', 0)}")
        print(f"   🔄 Running: {stats.get('running_jobs', 0)}")
        print(f"   ⏳ Pending: {stats.get('pending_jobs', 0)}")
        print(f"   ❌ Failed: {stats.get('failed_jobs', 0)}")
        print()

    # Get builder and property job counts
    builder_jobs = get_recent_jobs(entity_type="builder")
    property_jobs = get_recent_jobs(entity_type="property")

    print("🏗️  BUILDER COLLECTION JOBS")
    print("-"*80)
    builder_by_status = {}
    for job in builder_jobs:
        status = job.get("status", "unknown")
        builder_by_status[status] = builder_by_status.get(status, 0) + 1

    for status, count in sorted(builder_by_status.items()):
        emoji = {"completed": "✅", "running": "🔄", "pending": "⏳", "failed": "❌"}.get(status, "❓")
        print(f"   {emoji} {status.capitalize()}: {count}")

    print("\n🏘️  PROPERTY COLLECTION JOBS")
    print("-"*80)
    property_by_status = {}
    for job in property_jobs:
        status = job.get("status", "unknown")
        property_by_status[status] = property_by_status.get(status, 0) + 1

    for status, count in sorted(property_by_status.items()):
        emoji = {"completed": "✅", "running": "🔄", "pending": "⏳", "failed": "❌"}.get(status, "❓")
        print(f"   {emoji} {status.capitalize()}: {count}")

    # Show recent running/completed jobs
    print("\n📋 RECENT ACTIVITY (Last 10 Jobs)")
    print("-"*80)
    all_recent = builder_jobs[:5] + property_jobs[:5]
    all_recent = sorted(all_recent, key=lambda x: x.get("created_at", ""), reverse=True)[:10]

    for job in all_recent:
        status_emoji = {
            "completed": "✅",
            "running": "🔄",
            "pending": "⏳",
            "failed": "❌"
        }.get(job.get("status"), "❓")

        entity_emoji = {
            "builder": "🏗️ ",
            "property": "🏘️ ",
            "community": "📍"
        }.get(job.get("entity_type"), "❓")

        print(f"{status_emoji} {entity_emoji} {job.get('entity_type', 'N/A').capitalize()}: {job.get('search_query', 'N/A')[:50]}")
        print(f"      Status: {job.get('status')} | Items: {job.get('items_found', 0)} | Entities: {job.get('new_entities_found', 0)}")

    print("\n" + "="*80)

def monitor_continuous(interval=10):
    """Monitor jobs continuously with updates."""
    print("\n🔄 Starting continuous monitoring (Ctrl+C to stop)...")
    print(f"   Refresh interval: {interval} seconds\n")

    try:
        while True:
            # Clear screen (works on Unix-like systems)
            print("\033[2J\033[H", end="")

            display_progress()

            print(f"\n⏰ Next update in {interval} seconds... (Ctrl+C to stop)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring stopped by user")

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        monitor_continuous(interval)
    else:
        display_progress()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
