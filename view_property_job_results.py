"""
View Property Job Results with Details

This script shows properties collected by a property inventory job,
displaying all the detailed fields including builder plan name, move-in date, etc.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/v1"


def get_property_jobs():
    """Get all property inventory jobs."""
    response = requests.get(
        f"{BASE_URL}/admin/collection/jobs",
        params={
            "entity_type": "property",
            "job_type": "inventory",
            "limit": 20
        }
    )
    response.raise_for_status()
    return response.json()["jobs"]


def get_job_details(job_id):
    """Get details of a specific job."""
    response = requests.get(f"{BASE_URL}/admin/collection/jobs/{job_id}")
    response.raise_for_status()
    return response.json()


def get_properties_from_job(job_id):
    """Get properties collected by a job."""
    # Get changes from the job
    response = requests.get(f"{BASE_URL}/admin/collection/jobs/{job_id}/changes")
    response.raise_for_status()
    changes = response.json()

    # Extract unique property IDs
    property_ids = set()
    for change in changes:
        if change.get("entity_type") == "property" and change.get("entity_id"):
            property_ids.add(change["entity_id"])

    return list(property_ids)


def get_property_details(property_id):
    """Get full details of a property."""
    response = requests.get(f"{BASE_URL}/property/{property_id}")
    response.raise_for_status()
    return response.json()


def display_property_summary(prop):
    """Display a property summary with key details."""
    print("\n" + "=" * 80)
    print(f"📍 {prop.get('title', 'Untitled Property')}")
    print("=" * 80)

    # Basic Info
    print(f"\n💰 Price: ${prop.get('price', 0):,.2f}")
    print(f"📍 Location: {prop.get('address1', 'N/A')}, {prop.get('city', 'N/A')}, {prop.get('state', 'N/A')}")

    # Core Specs
    beds = prop.get('bedrooms', 'N/A')
    baths = prop.get('bathrooms', 'N/A')
    sqft = prop.get('sqft', 'N/A')
    print(f"🏠 Specs: {beds} bed | {baths} bath | {sqft:,} sqft" if isinstance(sqft, int) else f"🏠 Specs: {beds} bed | {baths} bath | {sqft} sqft")

    # Builder Information (NEW FIELDS)
    print("\n🏗️  BUILDER INFORMATION:")
    print(f"   Plan Name: {prop.get('builder_plan_name') or 'Not specified'}")
    print(f"   Series: {prop.get('builder_series') or 'Not specified'}")
    print(f"   Builder ID: {prop.get('builder_id') or 'N/A'}")
    print(f"   Community ID: {prop.get('community_id') or 'N/A'}")

    # Availability (NEW FIELDS)
    print("\n📅 AVAILABILITY:")
    print(f"   Move-in Date: {prop.get('move_in_date') or 'Not specified'}")
    print(f"   Listing Status: {prop.get('listing_status') or 'N/A'}")
    print(f"   Quick Move-In: {'Yes' if prop.get('quick_move_in') else 'No'}")
    print(f"   Model Home: {'Yes' if prop.get('model_home') else 'No'}")
    print(f"   Construction Stage: {prop.get('construction_stage') or 'N/A'}")

    # Property Details (NEW FIELDS)
    if any([prop.get('stories'), prop.get('garage_spaces'), prop.get('property_type')]):
        print("\n🏡 PROPERTY DETAILS:")
        if prop.get('property_type'):
            print(f"   Type: {prop.get('property_type')}")
        if prop.get('stories'):
            print(f"   Stories: {prop.get('stories')}")
        if prop.get('garage_spaces'):
            print(f"   Garage: {prop.get('garage_spaces')} spaces")

    # Features (NEW FIELDS)
    features = []
    if prop.get('game_room'):
        features.append("Game Room")
    if prop.get('study_office'):
        features.append("Study/Office")
    if prop.get('covered_patio'):
        features.append("Covered Patio")
    if prop.get('outdoor_kitchen'):
        features.append("Outdoor Kitchen")
    if prop.get('pool_type') and prop.get('pool_type') != 'none':
        features.append(f"{prop.get('pool_type').title()} Pool")

    if features:
        print("\n✨ FEATURES:")
        for feature in features:
            print(f"   • {feature}")

    # School Information (NEW FIELDS)
    if any([prop.get('school_district'), prop.get('elementary_school'),
            prop.get('middle_school'), prop.get('high_school')]):
        print("\n🎓 SCHOOLS:")
        if prop.get('school_district'):
            print(f"   District: {prop.get('school_district')}")
        if prop.get('elementary_school'):
            rating = prop.get('school_ratings', {}).get('elementary', '')
            rating_str = f" (Rating: {rating}/10)" if rating else ""
            print(f"   Elementary: {prop.get('elementary_school')}{rating_str}")
        if prop.get('middle_school'):
            rating = prop.get('school_ratings', {}).get('middle', '')
            rating_str = f" (Rating: {rating}/10)" if rating else ""
            print(f"   Middle: {prop.get('middle_school')}{rating_str}")
        if prop.get('high_school'):
            rating = prop.get('school_ratings', {}).get('high', '')
            rating_str = f" (Rating: {rating}/10)" if rating else ""
            print(f"   High: {prop.get('high_school')}{rating_str}")

    # Market Information (NEW FIELDS)
    if any([prop.get('builder_incentives'), prop.get('upgrades_included'),
            prop.get('days_on_market')]):
        print("\n💼 MARKET INFO:")
        if prop.get('days_on_market'):
            print(f"   Days on Market: {prop.get('days_on_market')}")
        if prop.get('builder_incentives'):
            print(f"   Incentives: {prop.get('builder_incentives')}")
        if prop.get('upgrades_included'):
            print(f"   Upgrades: {prop.get('upgrades_included')}")
        if prop.get('upgrades_value'):
            print(f"   Upgrades Value: ${prop.get('upgrades_value'):,.2f}")

    # Virtual Tours (NEW FIELDS)
    if any([prop.get('virtual_tour_url'), prop.get('floor_plan_url'),
            prop.get('matterport_link')]):
        print("\n🔗 VIRTUAL TOURS:")
        if prop.get('virtual_tour_url'):
            print(f"   Virtual Tour: {prop.get('virtual_tour_url')}")
        if prop.get('floor_plan_url'):
            print(f"   Floor Plan: {prop.get('floor_plan_url')}")
        if prop.get('matterport_link'):
            print(f"   Matterport: {prop.get('matterport_link')}")

    # Collection Metadata (NEW FIELDS)
    if any([prop.get('source_url'), prop.get('data_confidence')]):
        print("\n📊 COLLECTION METADATA:")
        if prop.get('source_url'):
            print(f"   Source: {prop.get('source_url')}")
        if prop.get('data_confidence'):
            confidence = prop.get('data_confidence') * 100
            print(f"   Data Confidence: {confidence:.0f}%")

    print("\n" + "-" * 80)


def main():
    print("=" * 80)
    print("PROPERTY JOB RESULTS VIEWER")
    print("=" * 80)

    try:
        # Get property inventory jobs
        print("\n📋 Fetching property inventory jobs...")
        jobs = get_property_jobs()

        if not jobs:
            print("❌ No property inventory jobs found")
            print("\n💡 Create property jobs using:")
            print("   python bulk_property_collection.py")
            return

        print(f"✅ Found {len(jobs)} property inventory jobs\n")

        # Display jobs
        for i, job in enumerate(jobs, 1):
            status_emoji = {
                "completed": "✅",
                "running": "🔄",
                "pending": "⏳",
                "failed": "❌"
            }.get(job["status"], "❓")

            print(f"{i}. {status_emoji} {job['job_id']}")
            print(f"   Status: {job['status']}")
            print(f"   Properties Found: {job.get('new_entities_found', 0)}")
            print(f"   Created: {job.get('created_at', 'N/A')[:19]}")

            # Get search filters to show builder/community
            job_details = get_job_details(job['job_id'])
            search_filters = json.loads(job_details.get('search_filters', '{}') or '{}')
            if search_filters.get('builder_id'):
                print(f"   Builder ID: {search_filters['builder_id']}")
            if search_filters.get('community_id'):
                print(f"   Community ID: {search_filters['community_id']}")
            print()

        # Ask user to select a job
        selection = input("\nEnter job number to view properties (or 'q' to quit): ").strip()

        if selection.lower() == 'q':
            return

        try:
            job_index = int(selection) - 1
            if job_index < 0 or job_index >= len(jobs):
                print("❌ Invalid selection")
                return

            selected_job = jobs[job_index]
            job_id = selected_job["job_id"]

            print(f"\n🔍 Fetching properties from job {job_id}...")

            # Get property IDs from this job
            property_ids = get_properties_from_job(job_id)

            if not property_ids:
                print("❌ No properties found in this job")
                return

            print(f"✅ Found {len(property_ids)} properties\n")

            # Fetch and display each property
            for prop_id in property_ids:
                try:
                    prop = get_property_details(prop_id)
                    display_property_summary(prop)
                except Exception as e:
                    print(f"❌ Error fetching property {prop_id}: {e}")

            print("\n" + "=" * 80)
            print(f"✅ Displayed {len(property_ids)} properties from job {job_id}")
            print("=" * 80)

        except ValueError:
            print("❌ Invalid input. Please enter a number.")

    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")


if __name__ == "__main__":
    main()
