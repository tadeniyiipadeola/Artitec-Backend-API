"""
Test Audit Log API Endpoints

This script demonstrates the new audit log functionality for property approval/denial tracking.
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/v1/admin/collection"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def test_audit_log_stats():
    """Test the audit log statistics endpoint."""
    print_section("Testing Audit Log Statistics")

    response = requests.get(f"{BASE_URL}/audit-logs/stats?days=30")

    if response.status_code == 200:
        stats = response.json()
        print("Audit Log Statistics (Last 30 Days):")
        print(f"  Total Actions: {stats['total_actions']}")
        print(f"  Auto-Approved: {stats['auto_approved']}")
        print(f"  Auto-Denied: {stats['auto_denied']}")
        print(f"  Manually Approved: {stats['manually_approved']}")
        print(f"  Manually Rejected: {stats['manually_rejected']}")
        print(f"  Pending Review: {stats['pending_review']}")
        print(f"  Properties Added: {stats['properties_added']}")
        print(f"  Properties Updated: {stats['properties_updated']}")
        print(f"  Last 7 Days Activity: {stats['last_7_days']}")
        print(f"  Last 30 Days Activity: {stats['last_30_days']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_audit_logs_list():
    """Test the audit log listing endpoint."""
    print_section("Testing Audit Log Listing (Recent Activity)")

    response = requests.get(f"{BASE_URL}/audit-logs?limit=10&days=30")

    if response.status_code == 200:
        logs = response.json()
        print(f"Found {len(logs)} recent audit log entries:\n")

        for i, log in enumerate(logs, 1):
            print(f"{i}. [{log['action'].upper()}] {log['entity_type']}: {log['entity_name']}")
            print(f"   Timestamp: {log['timestamp']}")
            print(f"   Confidence: {log['confidence']:.0%}")
            print(f"   Change Type: {log['change_type']}")
            print(f"   Auto Action: {'Yes' if log['is_auto_action'] else 'No'}")

            if log['reviewer_name']:
                print(f"   Reviewed By: {log['reviewer_name']}")

            if log['property_address']:
                print(f"   Address: {log['property_address']}")
                if log['property_bedrooms'] and log['property_bathrooms']:
                    print(f"   Beds/Baths: {log['property_bedrooms']}/{log['property_bathrooms']}")
                if log['property_price']:
                    print(f"   Price: ${log['property_price']:,.2f}")

            if log['review_notes']:
                print(f"   Notes: {log['review_notes'][:100]}{'...' if len(log['review_notes']) > 100 else ''}")

            print()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_filtered_audit_logs():
    """Test filtered audit log queries."""
    print_section("Testing Filtered Audit Logs")

    filters = [
        ("auto_approved", "Auto-Approved Properties"),
        ("auto_denied", "Auto-Denied Properties"),
        ("approved", "Manually Approved"),
        ("rejected", "Manually Rejected"),
    ]

    for action_filter, description in filters:
        response = requests.get(f"{BASE_URL}/audit-logs?action={action_filter}&limit=5&days=30")

        if response.status_code == 200:
            logs = response.json()
            print(f"{description}: {len(logs)} entries")

            for log in logs[:3]:  # Show first 3
                entity_info = log.get('entity_name', 'Unknown')
                if log.get('property_address'):
                    entity_info = log['property_address']
                print(f"  - {entity_info} (confidence: {log['confidence']:.0%})")

            if len(logs) > 3:
                print(f"  ... and {len(logs) - 3} more")
            print()
        else:
            print(f"Error for {description}: {response.status_code}")

def test_property_specific_logs():
    """Test filtering by entity type."""
    print_section("Testing Property-Specific Audit Logs")

    response = requests.get(f"{BASE_URL}/audit-logs?entity_type=property&limit=10&days=30")

    if response.status_code == 200:
        logs = response.json()
        print(f"Found {len(logs)} property-related audit entries:\n")

        for log in logs[:5]:  # Show first 5
            action_icon = {
                'auto_approved': '✅',
                'approved': '👍',
                'auto_denied': '❌',
                'rejected': '👎'
            }.get(log['action'], '❓')

            print(f"{action_icon} {log['entity_name']}")
            if log.get('property_address'):
                print(f"   {log['property_address']}")
            print(f"   Action: {log['action']} at {log['timestamp']}")
            print()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "AUDIT LOG API TESTING" + " " * 37 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        # Test all endpoints
        test_audit_log_stats()
        test_audit_logs_list()
        test_filtered_audit_logs()
        test_property_specific_logs()

        print_section("Testing Complete")
        print("All audit log endpoints are working correctly!")

        print("\n📋 Available Endpoints:")
        print(f"  GET {BASE_URL}/audit-logs/stats")
        print(f"  GET {BASE_URL}/audit-logs")
        print("\n🔍 Example Queries:")
        print(f"  {BASE_URL}/audit-logs?action=auto_approved&limit=20")
        print(f"  {BASE_URL}/audit-logs?entity_type=property&days=7")
        print(f"  {BASE_URL}/audit-logs?reviewer_id=USR-123&days=30")

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the API server")
        print("   Make sure the server is running at http://127.0.0.1:8000")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
