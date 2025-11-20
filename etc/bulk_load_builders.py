"""
Bulk load builders and associate them with their communities
"""
import pymysql
import os
import json
from dotenv import load_dotenv
from datetime import datetime

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

# Builder to Communities mapping
BUILDER_COMMUNITIES = {
    "Perry Homes": [
        "The Highlands", "Elyson", "Sienna Plantation", "Harvest Green",
        "The Woodlands Hills", "Meridiana", "Aliana", "Jordan Ranch",
        "Towne Lake", "Artavia", "West Ranch", "Balmoral", "Amira",
        "Bridgeland", "Woodson's Reserve", "Harper's Preserve", "Tavola", "Grand Mission"
    ],
    "Highland Homes": [
        "The Highlands", "Cross Creek Ranch", "Elyson", "Sienna Plantation",
        "Harvest Green", "The Woodlands Hills", "Meridiana", "Aliana",
        "Jordan Ranch", "Grand Central Park", "Artavia", "Evergreen",
        "Bridgeland", "Pomona", "Firethorne", "Harper's Preserve", "Walsh"
    ],
    "David Weekley Homes": [
        "The Highlands", "Elyson", "Sienna Plantation", "Harvest Green",
        "The Woodlands Hills", "Meridiana", "Jordan Ranch", "Artavia",
        "Bridgeland", "Pomona", "Cinco Ranch", "West Ranch", "Firethorne",
        "Grand Mission", "Veranda", "Walsh"
    ],
    "Lennar": [
        "The Highlands", "Cross Creek Ranch", "Elyson", "Harvest Green",
        "Aliana", "Jordan Ranch", "Towne Lake", "Evergreen", "Pomona",
        "Wildwood at Northpointe", "Cinco Ranch", "Balmoral", "Grand Mission", "Veranda"
    ],
    "Chesmar Homes": [
        "The Highlands", "Sienna Plantation", "The Woodlands Hills",
        "Meridiana", "Evergreen", "Balmoral", "Harper's Preserve", "Trinity Falls"
    ],
    "Westin Homes": [
        "Elyson", "The Woodlands Hills", "Meridiana", "Harvest Green",
        "Tuscan Lakes", "Balmoral", "Tavola"
    ],
    "Coventry Homes": [
        "The Highlands", "Bridgeland", "Meridiana", "Aliana", "Harvest Green",
        "Pomona", "Trinity Falls", "Firethorne", "Southgate", "Grand Mission"
    ],
    "Newmark Homes": [
        "The Highlands", "Cross Creek Ranch", "Elyson", "Towne Lake",
        "Harvest Green", "Meridiana", "Bridgeland", "Veranda"
    ],
    "Beazer Homes": [
        "The Highlands", "Bridgeland", "Amira"
    ],
    "Drees Homes": [
        "The Highlands", "Grand Central Park", "Meridiana", "Walsh"
    ],
    "Toll Brothers": [
        "Sienna Plantation", "Meridiana", "Woodson's Reserve", "Walsh"
    ],
    "J. Patrick Homes": [
        "The Highlands", "Sienna Plantation", "The Woodlands Hills",
        "Aliana", "Jordan Ranch", "Grand Central Park", "Artavia", "Harper's Preserve"
    ],
    "Ravenna Homes": [
        "The Highlands", "Bridgeland", "Towne Lake", "The Woodlands Hills"
    ],
    "Tri Pointe Homes": [
        "Bridgeland", "Harvest Green", "Woodson's Reserve"
    ],
    "Partners in Building": [
        "The Highlands", "Aliana", "Towne Lake", "West Ranch",
        "Firethorne", "Lakes of Bella Terra"
    ],
    "Village Builders": [
        "Harvest Green", "Aliana", "West Ranch", "Wildwood at Northpointe",
        "Cinco Ranch", "Lakes of Bella Terra", "Grand Mission", "Southgate", "Walsh"
    ],
    "Taylor Morrison": [
        "Cross Creek Ranch", "Elyson", "Riverstone", "Woodson's Reserve",
        "Fall Creek"
    ],
    "Shea Homes": [
        "Sienna Plantation", "Meridiana", "Evergreen"
    ],
    "Century Communities": [
        "Bridgeland", "The Woodlands Hills"
    ],
    "Brightland Homes": [
        "Bridgeland", "The Woodlands Hills", "Balmoral"
    ],
    "Ashton Woods": [
        "Aliana", "Balmoral", "Harper's Preserve", "Lakes of Bella Terra", "Firethorne"
    ],
    "Meritage Homes": [
        "Aliana", "Wildwood at Northpointe", "Woodson's Reserve", "Fall Creek"
    ],
    "Jamestown Estate Homes": [
        "Towne Lake", "Grand Central Park", "Artavia"
    ],
    "Pulte Homes": [
        "Elyson", "Tuscan Lakes"
    ],
    "K. Hovnanian Homes": [
        "Balmoral", "Lakes of Bella Terra", "Southgate"
    ],
    "Plantation Homes": [
        "Aliana", "Firethorne", "Harper's Preserve", "Grand Mission"
    ],
    "Sitterle Homes": [
        "Aliana", "Lakes of Bella Terra"
    ],
    "Fairmont Homes": [
        "Sienna Plantation", "Cinco Ranch"
    ],
    "Caldwell Homes": [
        "The Highlands"
    ],
    "Empire Homes": [
        "Sienna Plantation", "Southgate"
    ],
    "Tricoast Homes": [
        "Meridiana"
    ],
    "Psalms Fine Homes": [
        "Riverstone"
    ],
    "The Darling Collection": [
        "Riverstone"
    ],
    "Gehan Homes": [
        "Harper's Preserve"
    ],
    "D.R. Horton": [
        "Harper's Preserve", "Tuscan Lakes"
    ],
    "KB Home": [
        "Tuscan Lakes"
    ],
    "Del Webb": [
        "Trinity Falls", "Tuscan Lakes"
    ],
    "Cadence Homes": [
        "Trinity Falls"
    ],
    "Gracepoint Homes": [
        "Imperial"
    ],
    "M/I Homes": [
        "Wildwood at Northpointe", "Tavola"
    ],
    "Castle Rock Communities": [
        "Balmoral"
    ],
    "Hamilton Thomas Homes": [
        "Balmoral"
    ],
    "History Maker Homes": [
        "Balmoral"
    ],
    "Long Lake Ltd.": [
        "Balmoral"
    ],
    "Wan Bridge": [
        "Balmoral"
    ],
    "Parkwood Builders": [
        "Fall Creek"
    ],
    "Ryland Homes": [
        "Fall Creek"
    ],
    "Saratoga Homes": [
        "Fall Creek"
    ],
    "Trendmaker Homes": [
        "Cross Creek Ranch"
    ],
    "Britton Homes": [
        "Walsh"
    ],
    "Glendarroch Homes": [
        "Walsh"
    ],
    "HGC": [
        "Walsh"
    ],
    "High Street Homes": [
        "Walsh"
    ],
    "MK Homes": [
        "Walsh"
    ],
    "GFO Home": [
        "Walsh"
    ],
}

# Builder information
BUILDER_INFO = {
    "Perry Homes": {"website": "https://www.perryhomes.com"},
    "Highland Homes": {"website": "https://www.highlandhomes.com"},
    "David Weekley Homes": {"website": "https://www.davidweekleyhomes.com"},
    "Lennar": {"website": "https://www.lennar.com"},
    "Chesmar Homes": {"website": "https://chesmar.com"},
    "Westin Homes": {"website": "https://www.westin-homes.com"},
    "Coventry Homes": {"website": "https://www.coventryhomes.com"},
    "Newmark Homes": {"website": "https://newmarkhomes.com"},
    "Beazer Homes": {"website": "https://www.beazer.com"},
    "Toll Brothers": {"website": "https://www.tollbrothers.com"},
    "Taylor Morrison": {"website": "https://www.taylormorrison.com"},
    "Pulte Homes": {"website": "https://www.pulte.com"},
    "D.R. Horton": {"website": "https://www.drhorton.com"},
    "KB Home": {"website": "https://www.kbhome.com"},
    "Meritage Homes": {"website": "https://www.meritagehomes.com"},
    "Shea Homes": {"website": "https://www.sheahomes.com"},
    "Tri Pointe Homes": {"website": "https://www.tripointehomes.com"},
    "Century Communities": {"website": "https://www.centurycommunities.com"},
    "Ashton Woods": {"website": "https://www.ashtonwoods.com"},
    "J. Patrick Homes": {"website": "https://www.jpatrickhomes.com"},
}

print("=" * 80)
print("BULK LOADING BUILDERS AND COMMUNITY ASSOCIATIONS")
print("=" * 80)
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
        # Use specified admin user_id for all builders
        # Builders will claim their profiles later by creating accounts
        admin_user_id = "USR-1763447320-ELTNT2"
        print(f"Using admin user_id: {admin_user_id}")
        print("(Builders can claim profiles later by creating accounts)")
        print()

        # Step 1: Create all unique builders
        print("STEP 1: Creating Builder Profiles")
        print("-" * 80)

        builder_id_map = {}
        builders_created = 0
        builders_existing = 0

        for builder_name in sorted(BUILDER_COMMUNITIES.keys()):
            # Generate builder_id (external ID)
            builder_external_id = f"BLD-{builder_name.upper().replace(' ', '').replace('.', '')[:10]}-{hash(builder_name) % 10000:04d}"

            # Check if builder already exists by name
            cursor.execute(
                "SELECT id FROM builder_profiles WHERE name = %s",
                (builder_name,)
            )
            existing = cursor.fetchone()

            if existing:
                builder_id_map[builder_name] = existing['id']
                builders_existing += 1
                print(f"  ✓ Builder exists: {builder_name} (ID: {existing['id']})")
            else:
                # Get additional info
                info = BUILDER_INFO.get(builder_name, {})
                website = info.get('website', None)

                # Insert builder using actual schema
                cursor.execute("""
                    INSERT INTO builder_profiles (
                        builder_id, user_id, name, website, verified,
                        created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                """, (
                    builder_external_id,
                    admin_user_id,
                    builder_name,
                    website,
                    1  # verified = true
                ))

                builder_id_map[builder_name] = cursor.lastrowid
                builders_created += 1
                print(f"  ✓ Created: {builder_name} (ID: {cursor.lastrowid})")

        connection.commit()

        print()
        print(f"Builders created: {builders_created}")
        print(f"Builders already existed: {builders_existing}")
        print(f"Total unique builders: {len(builder_id_map)}")
        print()

        # Step 2: Associate builders with communities
        print("STEP 2: Creating Builder-Community Associations")
        print("-" * 80)

        associations_created = 0
        associations_existing = 0
        associations_failed = 0

        for builder_name, community_names in sorted(BUILDER_COMMUNITIES.items()):
            builder_db_id = builder_id_map.get(builder_name)

            if not builder_db_id:
                print(f"  ✗ Builder not found: {builder_name}")
                continue

            for community_name in community_names:
                # Find community by name
                cursor.execute(
                    "SELECT id FROM communities WHERE name = %s",
                    (community_name,)
                )
                community = cursor.fetchone()

                if not community:
                    print(f"  ✗ Community not found: {community_name}")
                    associations_failed += 1
                    continue

                community_db_id = community['id']

                # Check if association already exists
                cursor.execute("""
                    SELECT id FROM builder_communities
                    WHERE builder_id = %s AND community_id = %s
                """, (builder_db_id, community_db_id))

                existing_assoc = cursor.fetchone()

                if existing_assoc:
                    associations_existing += 1
                else:
                    # Create association
                    cursor.execute("""
                        INSERT INTO builder_communities (
                            builder_id, community_id, created_at, updated_at
                        ) VALUES (
                            %s, %s, NOW(), NOW()
                        )
                    """, (builder_db_id, community_db_id))

                    associations_created += 1
                    print(f"  ✓ {builder_name} -> {community_name}")

        connection.commit()

        print()
        print(f"Associations created: {associations_created}")
        print(f"Associations already existed: {associations_existing}")
        print(f"Associations failed (community not found): {associations_failed}")
        print()

        # Step 3: Update community_ids field in builder_profiles
        print("STEP 3: Updating community_ids Field in Builder Profiles")
        print("-" * 80)

        builders_updated = 0

        for builder_name, community_names in sorted(BUILDER_COMMUNITIES.items()):
            builder_db_id = builder_id_map.get(builder_name)

            if not builder_db_id:
                continue

            # Collect community IDs for this builder
            community_ids = []
            for community_name in community_names:
                cursor.execute(
                    "SELECT community_id FROM communities WHERE name = %s",
                    (community_name,)
                )
                community = cursor.fetchone()
                if community:
                    community_ids.append(community['community_id'])

            # Update builder_profiles with community_ids as JSON
            if community_ids:
                cursor.execute("""
                    UPDATE builder_profiles
                    SET community_ids = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(community_ids), builder_db_id))

                builders_updated += 1
                print(f"  ✓ Updated {builder_name}: {len(community_ids)} communities")

        connection.commit()

        print()
        print(f"Builders updated with community_ids: {builders_updated}")
        print()

        # Step 4: Summary
        print("STEP 4: Summary Statistics")
        print("-" * 80)

        cursor.execute("SELECT COUNT(*) as count FROM builder_profiles")
        total_builders = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM communities")
        total_communities = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM builder_communities")
        total_associations = cursor.fetchone()['count']

        cursor.execute("""
            SELECT
                bp.name,
                COUNT(bc.community_id) as community_count
            FROM builder_profiles bp
            LEFT JOIN builder_communities bc ON bp.id = bc.builder_id
            GROUP BY bp.id
            ORDER BY community_count DESC
            LIMIT 10
        """)
        top_builders = cursor.fetchall()

        print(f"Total Builders: {total_builders}")
        print(f"Total Communities: {total_communities}")
        print(f"Total Associations: {total_associations}")
        print()
        print("Top 10 Builders by Community Count:")
        for i, builder in enumerate(top_builders, 1):
            print(f"  {i}. {builder['name']}: {builder['community_count']} communities")

        print()
        print("=" * 80)
        print("COMPLETE!")
        print("=" * 80)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    connection.rollback()

finally:
    connection.close()
