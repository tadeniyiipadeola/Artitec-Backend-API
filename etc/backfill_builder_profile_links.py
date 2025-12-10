"""
Backfill builder_profile_id in community_builders table by matching with builder_profiles
"""
import pymysql
import os
import sys
from dotenv import load_dotenv
from difflib import SequenceMatcher

# Load environment variables
load_dotenv()

# Check for --yes flag
auto_confirm = "--yes" in sys.argv or "-y" in sys.argv

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

print(f"Connecting to database:")
print(f"  Host: {host}")
print(f"  Port: {port}")
print(f"  Database: {database}")
print(f"  User: {user}")
print()

def name_similarity(name1, name2):
    """Calculate similarity ratio between two names (0-1)"""
    if not name1 or not name2:
        return 0
    return SequenceMatcher(None, name1.lower().strip(), name2.lower().strip()).ratio()

# Connect to database
print("Connecting to database...")
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
        # Get all community_builders without builder_profile_id
        print("\nFetching community_builders without builder_profile_id...")
        cursor.execute("""
            SELECT id, name, community_id
            FROM community_builders
            WHERE builder_profile_id IS NULL
            ORDER BY community_id, name
        """)

        unlinked_cards = cursor.fetchall()
        print(f"  Found {len(unlinked_cards)} unlinked builder cards")

        if not unlinked_cards:
            print("\n✓ All builder cards are already linked!")
            exit(0)

        # Get all builder profiles
        print("\nFetching builder profiles...")
        cursor.execute("""
            SELECT id, builder_id, name, community_id
            FROM builder_profiles
            WHERE verified = 1
            ORDER BY name
        """)

        builder_profiles = cursor.fetchall()
        print(f"  Found {len(builder_profiles)} verified builder profiles")

        # Match and update
        print("\n" + "="*80)
        print("MATCHING BUILDER CARDS TO PROFILES")
        print("="*80)

        matches = []
        no_matches = []

        for card in unlinked_cards:
            card_id = card['id']
            card_name = card['name']
            card_community = card['community_id']

            best_match = None
            best_score = 0

            # Try to find matching builder profile
            for profile in builder_profiles:
                profile_id = profile['id']
                profile_name = profile['name']
                profile_community = profile['community_id']

                # Calculate name similarity
                name_score = name_similarity(card_name, profile_name)

                # Bonus points if community matches
                community_bonus = 0.2 if profile_community == card_community else 0

                total_score = name_score + community_bonus

                if total_score > best_score and name_score >= 0.8:  # Require at least 80% name match
                    best_score = total_score
                    best_match = {
                        'profile_id': profile_id,
                        'profile_name': profile_name,
                        'profile_builder_id': profile['builder_id'],
                        'name_similarity': name_score,
                        'community_match': profile_community == card_community
                    }

            if best_match:
                matches.append({
                    'card_id': card_id,
                    'card_name': card_name,
                    'card_community': card_community,
                    **best_match
                })
                print(f"\n✓ MATCH FOUND:")
                print(f"  Card ID: {card_id}")
                print(f"  Card Name: '{card_name}'")
                print(f"  → Profile ID: {best_match['profile_id']} ({best_match['profile_builder_id']})")
                print(f"  → Profile Name: '{best_match['profile_name']}'")
                print(f"  → Name Similarity: {best_match['name_similarity']:.2%}")
                print(f"  → Community Match: {best_match['community_match']}")
            else:
                no_matches.append({
                    'card_id': card_id,
                    'card_name': card_name,
                    'card_community': card_community
                })
                print(f"\n✗ NO MATCH:")
                print(f"  Card ID: {card_id}")
                print(f"  Card Name: '{card_name}'")
                print(f"  Community: {card_community}")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total unlinked cards: {len(unlinked_cards)}")
        print(f"Matches found: {len(matches)}")
        print(f"No matches: {len(no_matches)}")

        if no_matches:
            print("\nCards without matches:")
            for item in no_matches:
                print(f"  - {item['card_name']} (Community: {item['card_community']})")

        # Ask for confirmation
        if matches:
            print("\n" + "="*80)

            if auto_confirm:
                print(f"\nAuto-confirming update of {len(matches)} builder cards (--yes flag provided)")
                response = 'yes'
            else:
                response = input(f"\nDo you want to update {len(matches)} builder cards? (yes/no): ").strip().lower()

            if response == 'yes':
                print("\nUpdating builder_profile_id values...")
                updated = 0

                for match in matches:
                    cursor.execute("""
                        UPDATE community_builders
                        SET builder_profile_id = %s
                        WHERE id = %s
                    """, (match['profile_id'], match['card_id']))
                    updated += 1

                connection.commit()
                print(f"  ✓ Successfully updated {updated} builder cards")

                # Verify
                print("\nVerifying updates...")
                cursor.execute("""
                    SELECT
                        cb.id,
                        cb.name as card_name,
                        cb.builder_profile_id,
                        bp.builder_id,
                        bp.name as profile_name
                    FROM community_builders cb
                    LEFT JOIN builder_profiles bp ON cb.builder_profile_id = bp.id
                    WHERE cb.id IN (%s)
                """ % ','.join(str(m['card_id']) for m in matches[:5]))  # Show first 5

                samples = cursor.fetchall()
                print("  Sample of updated records:")
                for sample in samples:
                    print(f"    - Card '{sample['card_name']}' → Profile '{sample['profile_name']}' ({sample['builder_id']})")

            else:
                print("\n✗ Update cancelled by user")

        print("\n✓ Backfill process complete!")

finally:
    connection.close()
    print("\n✓ Database connection closed")
