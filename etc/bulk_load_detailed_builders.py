"""
Bulk Load Detailed Builder Profiles
Creates separate builder_profile entries for each builder-community combination
Total entries: 183+ (one per builder-community combination)
"""
import pymysql
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from complete_builder_community_data import BUILDER_COMMUNITY_DATA, ADMIN_USER_ID

# Load environment variables
load_dotenv()

# Parse DB URL
db_url = os.getenv("DB_URL")
parts = db_url.replace("mysql+pymysql://", "").split("@")
user_pass = parts[0].split(":")
user = user_pass[0]
password = user_pass[1]
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")
host = host_port[0]
port = int(host_port[1])
database = host_port_db[1]


def _create_builder_profile(cursor, builder_name, community_name, display_name,
                            community_data, website, about, specialties, communities_db):
    """Create a single builder profile entry"""

    # Look up community in database
    community_db = communities_db.get(community_name)
    if not community_db:
        print(f"  ⚠ Community not found: {community_name}")
        return False

    # Generate builder_id (external ID)
    builder_external_id = f"BLD-{builder_name.upper().replace(' ', '').replace('.', '')[:10]}-{hash(f'{builder_name}-{display_name}') % 10000:04d}"

    # Extract community-specific contact data
    address = community_data.get('address', '')
    city = community_data.get('city', community_db.get('city', ''))
    state = community_data.get('state', 'TX')
    postal_code = community_data.get('postal_code', '')
    phone = community_data.get('phone', '')
    email = community_data.get('email', '')
    title = community_data.get('title', 'Sales Office')
    note = community_data.get('note', '')

    # Build bio from contacts if available
    bio = ""
    contacts = community_data.get('contacts', [])
    if contacts:
        contact_names = [f"{c.get('name', '')} ({c.get('role', '')})" for c in contacts]
        bio = f"Contact: {', '.join(contact_names)}"

    # Add note to bio if exists
    if note:
        bio = f"{bio}. Note: {note}" if bio else f"Note: {note}"

    # Get community_id as plain string
    community_external_id = community_db.get('community_id')
    community_ids_value = community_external_id if community_external_id else None

    # Convert specialties to JSON array
    specialties_json = None
    if specialties:
        # Split by comma and create JSON array
        specialties_list = [s.strip() for s in specialties.split(',')]
        specialties_json = json.dumps(specialties_list)

    try:
        # Check if profile already exists
        cursor.execute(
            "SELECT id FROM builder_profiles WHERE name = %s AND city = %s AND address = %s",
            (builder_name, city, address)
        )
        existing = cursor.fetchone()

        if existing:
            print(f"  ⓘ Already exists: {builder_name} in {display_name}")
            return False

        # Insert builder profile
        cursor.execute("""
            INSERT INTO builder_profiles (
                builder_id, user_id, name, title, email, phone,
                address, city, state, postal_code,
                about, bio, website, verified, specialties,
                rating, community_ids,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s,
                NOW(), NOW()
            )
        """, (
            builder_external_id,
            ADMIN_USER_ID,
            builder_name,
            title,
            email,
            phone,
            address,
            city,
            state,
            postal_code,
            about,
            bio,
            website,
            1,  # verified = true
            specialties_json,
            None,  # rating starts as NULL
            community_ids_value
        ))

        builder_profile_id = cursor.lastrowid

        # Create builder_communities association
        cursor.execute("""
            INSERT INTO builder_communities (
                builder_id, community_id, created_at, updated_at
            ) VALUES (
                %s, %s, NOW(), NOW()
            )
        """, (builder_profile_id, community_db['id']))

        print(f"  ✓ Created: {builder_name} in {display_name} (ID: {builder_profile_id})")
        return True

    except Exception as e:
        print(f"  ✗ Error creating {builder_name} in {display_name}: {e}")
        return False


print("=" * 80)
print("BULK LOADING DETAILED BUILDER-COMMUNITY PROFILES")
print("=" * 80)
print()
print(f"Total builders: {len(BUILDER_COMMUNITY_DATA)}")
print(f"Admin user_id: {ADMIN_USER_ID}")
print()

# Connect to database
connection = pymysql.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        # Get all communities from database for mapping
        cursor.execute("SELECT id, community_id, name, city FROM communities")
        communities_db = {comm['name']: comm for comm in cursor.fetchall()}

        print(f"Found {len(communities_db)} communities in database")
        print()

        profiles_created = 0
        profiles_skipped = 0
        associations_created = 0

        # Process each builder
        for builder_name, builder_data in BUILDER_COMMUNITY_DATA.items():
            print(f"\nProcessing: {builder_name}")
            print("-" * 80)

            builder_website = builder_data.get('website')
            builder_about = builder_data.get('about')
            builder_specialties = builder_data.get('specialties')

            # Process each community for this builder
            for community_name, community_data in builder_data.get('communities', {}).items():
                # Handle sections (multiple sales offices in one community)
                if 'sections' in community_data:
                    for section in community_data['sections']:
                        section_name = section.get('name', '')
                        full_community_name = f"{community_name} - {section_name}"

                        # Create profile for this section
                        _create_builder_profile(
                            cursor,
                            builder_name,
                            community_name,
                            full_community_name,
                            section,
                            builder_website,
                            builder_about,
                            builder_specialties,
                            communities_db
                        )
                        profiles_created += 1
                else:
                    # Single office in community
                    _create_builder_profile(
                        cursor,
                        builder_name,
                        community_name,
                        community_name,
                        community_data,
                        builder_website,
                        builder_about,
                        builder_specialties,
                        communities_db
                    )
                    profiles_created += 1

        connection.commit()

        print()
        print("=" * 80)
        print("BULK LOAD COMPLETE!")
        print("=" * 80)
        print(f"Profiles created: {profiles_created}")
        print(f"Profiles skipped: {profiles_skipped}")
        print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    connection.rollback()

finally:
    connection.close()
