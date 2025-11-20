"""
Test the new /communities/available endpoint
"""
import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@artitec.com"  # Replace with actual admin email
ADMIN_PASSWORD = "admin123"  # Replace with actual admin password

print("="*80)
print("TESTING COMMUNITIES ENDPOINT FOR ENTERPRISE BUILDER PROVISIONING")
print("="*80)
print()

# Step 1: Login as admin
print("Step 1: Logging in as admin...")
login_response = requests.post(
    f"{BASE_URL}/v1/auth/login",
    json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(f"Response: {login_response.text}")
    exit(1)

login_data = login_response.json()
access_token = login_data.get("access_token")
print(f"✓ Logged in successfully")
print()

# Step 2: Fetch available communities
print("Step 2: Fetching available communities...")
communities_response = requests.get(
    f"{BASE_URL}/v1/admin/communities/available",
    headers={
        "Authorization": f"Bearer {access_token}"
    }
)

if communities_response.status_code != 200:
    print(f"❌ Failed to fetch communities: {communities_response.status_code}")
    print(f"Response: {communities_response.text}")
    exit(1)

communities = communities_response.json()
print(f"✓ Successfully fetched {len(communities)} communities")
print()

# Step 3: Display communities
print("Available Communities:")
print("-" * 80)
for i, community in enumerate(communities, 1):
    print(f"{i}. {community['name']}")
    print(f"   ID: {community['community_id']}")
    print(f"   Location: {community['city']}, {community['state']}")
    print()

# Step 4: Show sample usage for provisioning
print("="*80)
print("SAMPLE USAGE FOR ENTERPRISE BUILDER PROVISIONING")
print("="*80)
print()
print("To provision an enterprise builder with community assignments:")
print()
print("POST /v1/admin/builders/enterprise/provision")
print("Headers: Authorization: Bearer <access_token>")
print("Body:")
print(json.dumps({
    "company_name": "Perry Homes",
    "website_url": "https://www.perryhomes.com",
    "company_address": "2222 Quitman St, Houston, TX 77009",
    "primary_contact_email": "john.doe@perryhomes.com",
    "primary_contact_first_name": "John",
    "primary_contact_last_name": "Doe",
    "primary_contact_phone": "+12815551234",
    "plan_tier": "enterprise",
    "community_ids": [communities[0]["community_id"], communities[1]["community_id"]] if len(communities) >= 2 else [],
    "invitation_expires_days": 7
}, indent=2))
print()
print("This will:")
print("  1. Create the Perry Homes builder profile")
print("  2. Create the primary user account")
print("  3. Associate the builder with the selected communities")
print("  4. Generate an invitation code for the primary contact")
print()
print("="*80)
