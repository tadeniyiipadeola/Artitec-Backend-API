#!/usr/bin/env python3
"""
Test script to verify moderation_status enum fix
"""

import requests
import json

# Test 1: Health check
print("=" * 60)
print("Test 1: API Health Check")
print("=" * 60)
try:
    response = requests.get("http://127.0.0.1:8000/health")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Server is running")
    else:
        print(f"❌ Server returned {response.status_code}")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit(1)

# Test 2: List media for community 3
print("\n" + "=" * 60)
print("Test 2: List Media for Community 3")
print("=" * 60)
try:
    response = requests.get("http://127.0.0.1:8000/v1/media/entity/community/3")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved {data.get('total', 0)} media items")

        if data.get('items'):
            first_item = data['items'][0]
            print(f"\nFirst item details:")
            print(f"  - public_id: {first_item.get('public_id')}")
            print(f"  - moderation_status: {first_item.get('moderation_status')}")
            print(f"  - storage_type: {first_item.get('storage_type')}")
            print(f"  - is_approved: {first_item.get('is_approved')}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Try scraping a single image
print("\n" + "=" * 60)
print("Test 3: Scrape Single Image")
print("=" * 60)

scrape_payload = {
    "entityType": "community",
    "entityId": 3,
    "urls": ["https://picsum.photos/800/600"]  # Random test image
}

try:
    response = requests.post(
        "http://127.0.0.1:8000/v1/media/scrape",
        json=scrape_payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data.get('message')}")
        print(f"   Media count: {data.get('mediaCount', data.get('media_count', 0))}")

        if data.get('media'):
            for item in data['media']:
                print(f"\n   Scraped media:")
                print(f"     - public_id: {item.get('public_id')}")
                print(f"     - moderation_status: {item.get('moderation_status', item.get('moderationStatus'))}")
                print(f"     - storage_type: {item.get('storage_type', item.get('storageType'))}")
                print(f"     - is_approved: {item.get('is_approved', item.get('isApproved'))}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Testing Complete")
print("=" * 60)
