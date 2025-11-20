"""
Create detailed builder profiles with separate entries for each community
Each builder-community combination will have its own complete profile
"""

# Builder-Community detailed structure
# Each entry represents one builder in one specific community
BUILDER_COMMUNITY_PROFILES = {
    "Perry Homes": {
        "communities": [
            "The Highlands", "Elyson", "Sienna Plantation", "Harvest Green",
            "The Woodlands Hills", "Meridiana", "Aliana", "Jordan Ranch",
            "Towne Lake", "Artavia", "West Ranch", "Balmoral", "Amira",
            "Bridgeland", "Woodson's Reserve", "Harper's Preserve"
        ],
        "website": "https://www.perryhomes.com"
    },
    "Highland Homes": {
        "communities": [
            "The Highlands", "Cross Creek Ranch", "Elyson", "Sienna Plantation",
            "Harvest Green", "The Woodlands Hills", "Meridiana", "Aliana",
            "Jordan Ranch", "Grand Central Park", "Artavia", "Evergreen",
            "Bridgeland", "Pomona", "Harper's Preserve"
        ],
        "website": "https://www.highlandhomes.com"
    },
    "David Weekley Homes": {
        "communities": [
            "The Highlands", "Elyson", "Sienna Plantation", "Harvest Green",
            "The Woodlands Hills", "Meridiana", "Jordan Ranch", "Artavia",
            "Bridgeland", "Pomona", "Cinco Ranch", "West Ranch"
        ],
        "website": "https://www.davidweekleyhomes.com"
    },
    "Lennar": {
        "communities": [
            "The Highlands", "Cross Creek Ranch", "Elyson", "Harvest Green",
            "Aliana", "Jordan Ranch", "Towne Lake", "Evergreen", "Pomona",
            "Wildwood at Northpointe", "Cinco Ranch", "Balmoral"
        ],
        "website": "https://www.lennar.com"
    },
    # Add more builders...
}

# Template for each builder-community profile entry
PROFILE_TEMPLATE = {
    "builder_id": "",  # BLD-XXX format
    "user_id": "USR-1763447320-ELTNT2",  # Admin user
    "name": "",  # Builder name
    "title": "",  # e.g., "Sales Representative", "Community Manager"
    "email": "",  # Community-specific email
    "phone": "",  # Community-specific phone
    "address": "",  # Builder's office address in this community
    "city": "",
    "state": "",
    "postal_code": "",
    "about": "",  # About this builder
    "bio": "",  # Bio of local representative
    "website": "",  # Builder website
    "verified": True,
    "specialties": "",  # e.g., "Custom Homes, Energy Efficient"
    "rating": None,
    "community_ids": [],  # JSON array with this specific community
    "socials": None  # JSON with social media links
}

print("=" * 80)
print("BUILDER-COMMUNITY PROFILE STRUCTURE")
print("=" * 80)
print()
print("Total builders to research:")
for builder, data in BUILDER_COMMUNITY_PROFILES.items():
    print(f"  {builder}: {len(data['communities'])} communities")
print()
print("This requires researching each builder's specific office/contact")
print("information for each community they build in.")
print()
print("Fields to research for each builder-community combination:")
print("  - Office address in the community")
print("  - Local phone number")
print("  - Local email contact")
print("  - Sales representative name/title")
print("  - Community-specific information")
print()
