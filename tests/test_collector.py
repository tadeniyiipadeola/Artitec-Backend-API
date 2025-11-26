#!/usr/bin/env python3
"""
Test Collection System

Direct test of the collection job execution without using the API.
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import DB_URL
from model.collection import CollectionJob
from src.collection.job_executor import JobExecutor, create_community_collection_job

def test_anthropic_api():
    """Test Anthropic API connection"""
    print("\n" + "="*60)
    print("TEST 1: Anthropic API Connection")
    print("="*60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set in environment")
        return False

    print(f"✅ API Key found: {api_key[:20]}...")

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        print("📡 Testing API call...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'Hello' in one word."}]
        )

        response = message.content[0].text
        print(f"✅ API Response: {response}")
        print(f"✅ Model: {message.model}")
        print(f"✅ Tokens: {message.usage.input_tokens} in, {message.usage.output_tokens} out")
        return True

    except Exception as e:
        print(f"❌ API Error: {e}")
        return False


def test_database_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("TEST 2: Database Connection")
    print("="*60)

    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        db = Session()

        # Try to query jobs
        job_count = db.query(CollectionJob).count()
        print(f"✅ Database connected")
        print(f"✅ Total jobs in database: {job_count}")

        # Show recent jobs
        recent_jobs = db.query(CollectionJob).order_by(
            CollectionJob.created_at.desc()
        ).limit(3).all()

        if recent_jobs:
            print(f"\n📋 Recent jobs:")
            for job in recent_jobs:
                print(f"  - {job.job_id}: {job.status} ({job.entity_type}/{job.job_type})")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False


def test_create_job():
    """Test creating a collection job"""
    print("\n" + "="*60)
    print("TEST 3: Create Collection Job")
    print("="*60)

    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        db = Session()

        print("📝 Creating test community collection job...")
        job = create_community_collection_job(
            db=db,
            location="Dallas, TX",
            initiated_by="test_script"
        )

        print(f"✅ Job created: {job.job_id}")
        print(f"   Entity Type: {job.entity_type}")
        print(f"   Job Type: {job.job_type}")
        print(f"   Status: {job.status}")
        print(f"   Priority: {job.priority}")

        db.close()
        return job.job_id

    except Exception as e:
        print(f"❌ Job Creation Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_execute_job(job_id):
    """Test executing a collection job"""
    print("\n" + "="*60)
    print("TEST 4: Execute Collection Job")
    print("="*60)

    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        db = Session()

        executor = JobExecutor(db)

        print(f"🚀 Executing job: {job_id}")
        print("⏳ This may take 30-60 seconds...")

        executor.execute_job(job_id)

        # Check job status
        job = db.query(CollectionJob).filter(
            CollectionJob.job_id == job_id
        ).first()

        print(f"\n✅ Job execution completed!")
        print(f"   Status: {job.status}")
        print(f"   Items Found: {job.items_found}")
        print(f"   New Entities: {job.new_entities_found}")
        print(f"   Changes Detected: {job.changes_detected}")

        if job.error_message:
            print(f"   Error: {job.error_message}")

        db.close()
        return job.status == "completed"

    except Exception as e:
        print(f"❌ Job Execution Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("COLLECTION SYSTEM TEST SUITE")
    print("="*60)

    # Test 1: API Connection
    if not test_anthropic_api():
        print("\n⚠️  API test failed. Fix API configuration before proceeding.")
        return

    # Test 2: Database Connection
    if not test_database_connection():
        print("\n⚠️  Database test failed. Fix database configuration.")
        return

    # Test 3: Create Job
    job_id = test_create_job()
    if not job_id:
        print("\n⚠️  Job creation failed.")
        return

    # Test 4: Execute Job
    print("\n" + "="*60)
    print("READY TO EXECUTE JOB")
    print("="*60)
    response = input(f"\nExecute job {job_id}? (y/n): ")

    if response.lower() == 'y':
        success = test_execute_job(job_id)

        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)

        if success:
            print("✅ All tests passed!")
            print("✅ Collection system is working correctly")
        else:
            print("❌ Job execution failed")
            print("⚠️  Check error messages above")
    else:
        print(f"\n⚠️  Skipped execution. Job {job_id} remains pending.")
        print(f"   You can execute it later via API or UI.")

    print("\n" + "="*60)


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    run_all_tests()
