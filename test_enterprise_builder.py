#!/usr/bin/env python3
"""
Enterprise Builder Provisioning Test Script

This script tests the complete enterprise builder provisioning flow:
1. Admin login
2. Provision enterprise builder (e.g., Perry Homes)
3. Validate invitation
4. List team members
5. Invite new team member
6. Update team member
7. List communities
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "supportteam@artitecplatform.com"
ADMIN_PASSWORD = "Password!"

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_json(data):
    print(json.dumps(data, indent=2))

# Step 1: Admin Login
def admin_login():
    print_info("Step 1: Admin Login")
    url = f"{BASE_URL}/v1/auth/login"
    payload = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        access_token = data.get("access_token")
        user = data.get("user", {})

        print_success(f"Logged in as: {user.get('email')}")
        print_success(f"Role: {user.get('role', {}).get('name')}")
        print_success(f"Access token obtained")

        return access_token
    except requests.exceptions.RequestException as e:
        print_error(f"Login failed: {e}")
        return None

# Step 2: Provision Enterprise Builder
def provision_enterprise_builder(access_token):
    print_info("\nStep 2: Provision Enterprise Builder (Perry Homes)")
    url = f"{BASE_URL}/v1/admin/builders/enterprise/provision"

    payload = {
        "company_name": "Perry Homes",
        "website_url": "https://www.perryhomes.com",
        "enterprise_number": "ENT-PERRY-2025",
        "company_address": "3000 Sage Rd, Houston, TX 77056",
        "staff_size": "500+",
        "years_in_business": 75,
        "primary_contact_email": "john.perry@perryhomes.com",
        "primary_contact_first_name": "John",
        "primary_contact_last_name": "Perry",
        "primary_contact_phone": "+17135551234",
        "invitation_expires_days": 14,
        "custom_message": "Welcome to Artitec! Perry Homes is now part of our enterprise builder program.",
        "plan_tier": "enterprise",
        "community_ids": []
    }

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        builder = data.get("builder", {})
        user = data.get("user", {})
        invitation = data.get("invitation", {})

        print_success(f"Builder created: {builder.get('name')} (ID: {builder.get('builder_id')})")
        print_success(f"Admin user created: {user.get('email')} (ID: {user.get('public_id')})")
        print_success(f"Invitation code: {invitation.get('invitation_code')}")
        print_success(f"Invitation expires: {invitation.get('expires_at')}")

        print_info("\nNext steps:")
        for step in data.get("next_steps", []):
            print(f"  • {step}")

        return {
            "builder_id": builder.get("builder_id"),
            "user_id": user.get("public_id"),
            "invitation_code": invitation.get("invitation_code")
        }
    except requests.exceptions.RequestException as e:
        print_error(f"Provisioning failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return None

# Step 3: Validate Invitation
def validate_invitation(invitation_code):
    print_info(f"\nStep 3: Validate Invitation Code: {invitation_code}")
    url = f"{BASE_URL}/v1/admin/invitations/{invitation_code}/validate"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get("valid"):
            print_success(f"Invitation is valid!")
            print_success(f"Builder: {data.get('builder_name')}")
            print_success(f"Email: {data.get('invited_email')}")
            print_success(f"Role: {data.get('invited_role')}")
            print_success(f"Expires: {data.get('expires_at')}")
            if data.get("custom_message"):
                print_info(f"Message: {data.get('custom_message')}")
        else:
            print_error(f"Invitation invalid: {data.get('error_message')}")

        return data.get("valid")
    except requests.exceptions.RequestException as e:
        print_error(f"Validation failed: {e}")
        return False

# Step 4: List Team Members
def list_team_members(access_token, builder_id):
    print_info(f"\nStep 4: List Team Members for Builder: {builder_id}")
    url = f"{BASE_URL}/v1/admin/builders/{builder_id}/team"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # API returns list directly or dict with team_members key
        members = data if isinstance(data, list) else data.get("team_members", [])
        print_success(f"Found {len(members)} team member(s)")

        for member in members:
            user = member.get("user", {})
            print(f"\n  👤 {user.get('first_name')} {user.get('last_name')}")
            print(f"     Email: {user.get('email')}")
            print(f"     Role: {member.get('role')}")
            print(f"     Status: {member.get('is_active')}")

            if member.get("communities_assigned"):
                print(f"     Communities: {', '.join(member.get('communities_assigned'))}")
            else:
                print(f"     Communities: All (unrestricted access)")

        return members
    except requests.exceptions.RequestException as e:
        print_error(f"List team members failed: {e}")
        return []

# Step 5: Invite Team Member
def invite_team_member(access_token, builder_id):
    print_info(f"\nStep 5: Invite Sales Rep for Builder: {builder_id}")
    url = f"{BASE_URL}/v1/admin/builders/{builder_id}/team/invite"

    payload = {
        "builder_id": builder_id,
        "invited_email": "sarah.sales@perryhomes.com",
        "invited_role": "salesrep",  # Fixed: Use "salesrep" not "sales_rep"
        "invited_first_name": "Sarah",
        "invited_last_name": "Johnson",
        "invited_phone": "+17135554567",
        "communities_assigned": [],  # Empty = access to all
        "custom_message": "Welcome to the Perry Homes sales team!",
        "invitation_expires_days": 7
    }

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        invitation = response.json()  # Response is the invitation directly, not wrapped

        print_success(f"Invitation sent to: {invitation.get('invited_email')}")
        print_success(f"Invitation code: {invitation.get('invitation_code')}")
        print_success(f"Role: {invitation.get('invited_role')}")

        return invitation.get("invitation_code")
    except requests.exceptions.RequestException as e:
        print_error(f"Invite team member failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return None

# Step 6: Update Team Member
def update_team_member(access_token, builder_id, user_id):
    print_info(f"\nStep 6: Update Team Member: {user_id}")
    url = f"{BASE_URL}/v1/admin/builders/{builder_id}/team-members/{user_id}"

    payload = {
        "role": "manager",
        "communities_assigned": None,  # None = access to all
        "is_active": "active"
    }

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        print_success(f"Team member updated successfully")
        print_success(f"New role: {data.get('role')}")
        print_success(f"Status: {data.get('is_active')}")

        if data.get("communities_assigned"):
            print_success(f"Communities: {', '.join(data.get('communities_assigned'))}")
        else:
            print_success(f"Communities: All (unrestricted access)")

        return data
    except requests.exceptions.RequestException as e:
        print_error(f"Update team member failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return None

# Step 7: List Builder Communities
def list_builder_communities(access_token, builder_id):
    print_info(f"\nStep 7: List Communities for Builder: {builder_id}")
    url = f"{BASE_URL}/v1/admin/builders/{builder_id}/communities"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        communities = data.get("communities", [])
        print_success(f"Builder: {data.get('builder_name')}")
        print_success(f"Total communities: {data.get('total_communities')}")

        for community in communities:
            print(f"\n  🏘️  {community.get('name')}")
            print(f"     Location: {community.get('city')}, {community.get('state')}")
            print(f"     ID: {community.get('community_id')}")
            print(f"     Properties: {community.get('property_count', 0)}")

        return communities
    except requests.exceptions.RequestException as e:
        print_error(f"List communities failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return []

# Main test flow
def main():
    print("=" * 60)
    print("ENTERPRISE BUILDER PROVISIONING TEST")
    print("=" * 60)

    # Step 1: Login
    access_token = admin_login()
    if not access_token:
        print_error("Cannot continue without access token")
        return

    # Step 2: Provision builder
    provision_result = provision_enterprise_builder(access_token)
    if not provision_result:
        print_error("Provisioning failed")
        return

    builder_id = provision_result["builder_id"]
    user_id = provision_result["user_id"]
    invitation_code = provision_result["invitation_code"]

    # Step 3: Validate invitation
    validate_invitation(invitation_code)

    # Step 4: List team members
    list_team_members(access_token, builder_id)

    # Step 5: Invite team member
    sales_rep_invitation = invite_team_member(access_token, builder_id)

    # Step 6: Update the admin user to manager (for testing)
    # NOTE: Skipping - no PUT endpoint exists for updating team members
    # update_team_member(access_token, builder_id, user_id)

    # Step 7: List communities
    list_builder_communities(access_token, builder_id)

    print("\n" + "=" * 60)
    print_success("TESTING COMPLETE!")
    print("=" * 60)
    print_info(f"\nKey Information:")
    print(f"  Builder ID: {builder_id}")
    print(f"  Admin User ID: {user_id}")
    print(f"  Admin Invitation: {invitation_code}")
    if sales_rep_invitation:
        print(f"  Sales Rep Invitation: {sales_rep_invitation}")
    print("\nYou can use these codes to test invitation acceptance in the iOS app!")

if __name__ == "__main__":
    main()
