#!/usr/bin/env python3
"""
Simple Collection Test

Tests the collector directly via API without model imports.
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:8000"


def test_api_health():
    """Test API is running"""
    print("\n" + "="*60)
    print("TEST 1: API Health Check")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ API is running (Status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ API is not running")
        print("   Start the backend with: uvicorn src.app:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_anthropic_api():
    """Test Anthropic API key"""
    print("\n" + "="*60)
    print("TEST 2: Anthropic API Key")
    print("="*60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return False

    print(f"✅ API Key: {api_key[:20]}...")

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say hi"}]
        )

        print(f"✅ Response: {message.content[0].text}")
        print(f"✅ Model: {message.model}")
        return True

    except Exception as e:
        print(f"❌ API Error: {e}")
        return False


def test_create_job():
    """Test creating a job via API"""
    print("\n" + "="*60)
    print("TEST 3: Create Collection Job")
    print("="*60)

    payload = {
        "entity_type": "community",
        "job_type": "discovery",
        "location": "Dallas, TX",
        "priority": 7
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v1/admin/collection/jobs",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            job = response.json()
            print(f"✅ Job created: {job['job_id']}")
            print(f"   Status: {job['status']}")
            print(f"   Entity Type: {job['entity_type']}")
            return job['job_id']
        else:
            print(f"❌ Failed to create job: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_execute_job(job_id):
    """Test executing a specific job"""
    print("\n" + "="*60)
    print("TEST 4: Execute Specific Job")
    print("="*60)

    try:
        # First, get the job details
        response = requests.get(
            f"{BASE_URL}/v1/admin/collection/jobs/{job_id}",
            timeout=10
        )

        if response.status_code != 200:
            print(f"❌ Job not found: {job_id}")
            return False

        print(f"✅ Job found: {job_id}")

        # Execute the job
        print("🚀 Executing job...")
        print("⏳ This may take 30-60 seconds...")

        response = requests.post(
            f"{BASE_URL}/v1/admin/collection/jobs/execute-pending?limit=10",
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Execution completed!")
            print(f"   Total Pending: {result.get('total_pending', 0)}")
            print(f"   Executed: {result.get('executed', 0)}")
            print(f"   Failed: {result.get('failed', 0)}")

            if result.get('errors'):
                print(f"\n❌ Errors:")
                for error in result['errors']:
                    print(f"   {error}")

            # Get job status again
            response = requests.get(
                f"{BASE_URL}/v1/admin/collection/jobs/{job_id}",
                timeout=10
            )

            if response.status_code == 200:
                job = response.json()
                print(f"\n📊 Job Results:")
                print(f"   Status: {job['status']}")
                print(f"   Items Found: {job['items_found']}")
                print(f"   New Entities: {job['new_entities_found']}")
                print(f"   Changes Detected: {job['changes_detected']}")

                if job.get('error_message'):
                    print(f"   Error: {job['error_message']}")

                return job['status'] == 'completed'

        else:
            print(f"❌ Execution failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_jobs():
    """List all jobs"""
    print("\n" + "="*60)
    print("BONUS: List All Jobs")
    print("="*60)

    try:
        response = requests.get(
            f"{BASE_URL}/v1/admin/collection/jobs?page=1&page_size=5",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            jobs = data['jobs']

            print(f"✅ Found {data['total']} total jobs")
            print(f"\n📋 Recent Jobs:")

            for job in jobs[:5]:
                status_icon = {
                    'pending': '⏳',
                    'running': '🔄',
                    'completed': '✅',
                    'failed': '❌',
                    'cancelled': '🚫'
                }.get(job['status'], '❓')

                print(f"   {status_icon} {job['job_id']}: {job['status']} - {job['entity_type']}/{job['job_type']}")

                if job['status'] == 'completed':
                    print(f"      Items: {job['items_found']}, New: {job['new_entities_found']}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def run_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("COLLECTION SYSTEM TEST - SIMPLE VERSION")
    print("="*60)

    # Test 1: API Health
    if not test_api_health():
        print("\n⚠️  Make sure the backend is running!")
        return

    # Test 2: Anthropic API
    if not test_anthropic_api():
        print("\n⚠️  Fix Anthropic API configuration")
        return

    # Test 3: Create Job
    job_id = test_create_job()
    if not job_id:
        print("\n⚠️  Failed to create job")
        return

    # Test 4: Execute Job
    print("\n" + "="*60)
    print("READY TO EXECUTE JOB")
    print("="*60)
    print(f"Job ID: {job_id}")
    response = input("\nExecute this job? (y/n): ")

    if response.lower() == 'y':
        success = test_execute_job(job_id)

        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)

        if success:
            print("✅ All tests passed!")
            print("✅ Collection system is working correctly")
        else:
            print("❌ Job execution had issues")
            print("⚠️  Check error messages above")

        # Bonus: Show all jobs
        test_get_jobs()

    else:
        print(f"\n⚠️  Job {job_id} created but not executed")
        test_get_jobs()

    print("\n" + "="*60)


if __name__ == "__main__":
    run_tests()
