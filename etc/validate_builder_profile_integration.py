"""
Validation Script: Verify builder_profile_id integration
Tests the complete integration between community_builders and builder_profiles.
"""
import pymysql
import os
from dotenv import load_dotenv

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

print("=" * 80)
print("BUILDER PROFILE INTEGRATION VALIDATION")
print("=" * 80)
print(f"\nConnecting to database: {host}:{port}/{database}")

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
        print("\n" + "=" * 80)
        print("TEST 1: Schema Validation")
        print("=" * 80)

        # Check if builder_profile_id column exists
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'community_builders'
            AND COLUMN_NAME IN ('builder_profile_id', 'created_at', 'updated_at')
            ORDER BY COLUMN_NAME
        """, (database,))

        columns = cursor.fetchall()
        if len(columns) == 3:
            print("✅ All required columns exist:")
            for col in columns:
                print(f"   - {col['COLUMN_NAME']}: {col['COLUMN_TYPE']} {col['COLUMN_KEY']}")
        else:
            print(f"❌ Missing columns. Found {len(columns)}/3 expected columns")
            connection.close()
            exit(1)

        # Check foreign key constraint
        cursor.execute("""
            SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'community_builders'
            AND COLUMN_NAME = 'builder_profile_id'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (database,))

        fk = cursor.fetchone()
        if fk:
            print(f"✅ Foreign key constraint exists: {fk['CONSTRAINT_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")
        else:
            print("❌ Foreign key constraint not found")

        # Check index
        cursor.execute("""
            SELECT INDEX_NAME, COLUMN_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'community_builders'
            AND COLUMN_NAME = 'builder_profile_id'
        """, (database,))

        index = cursor.fetchone()
        if index:
            print(f"✅ Index exists: {index['INDEX_NAME']}")
        else:
            print("⚠️  Index not found (recommended for performance)")

        print("\n" + "=" * 80)
        print("TEST 2: Data Integrity")
        print("=" * 80)

        # Count total builder cards
        cursor.execute("SELECT COUNT(*) as count FROM community_builders")
        total_cards = cursor.fetchone()['count']
        print(f"Total builder cards: {total_cards}")

        # Count linked cards
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM community_builders
            WHERE builder_profile_id IS NOT NULL
        """)
        linked_cards = cursor.fetchone()['count']
        print(f"Linked to profiles: {linked_cards} ({100 * linked_cards / total_cards if total_cards > 0 else 0:.1f}%)")

        # Count unlinked cards
        unlinked_cards = total_cards - linked_cards
        print(f"Unlinked cards: {unlinked_cards} ({100 * unlinked_cards / total_cards if total_cards > 0 else 0:.1f}%)")

        # Check for broken links (builder_profile_id points to non-existent profile)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM community_builders cb
            LEFT JOIN builder_profiles bp ON cb.builder_profile_id = bp.id
            WHERE cb.builder_profile_id IS NOT NULL
            AND bp.id IS NULL
        """)
        broken_links = cursor.fetchone()['count']
        if broken_links == 0:
            print(f"✅ No broken links (all builder_profile_id values reference valid profiles)")
        else:
            print(f"❌ Found {broken_links} broken links (cards pointing to non-existent profiles)")

        print("\n" + "=" * 80)
        print("TEST 3: Relationship Validation")
        print("=" * 80)

        # Sample 5 linked cards and verify the relationship
        cursor.execute("""
            SELECT
                cb.id as card_id,
                cb.name as card_name,
                cb.builder_profile_id,
                bp.id as profile_id,
                bp.builder_id as profile_builder_id,
                bp.name as profile_name
            FROM community_builders cb
            INNER JOIN builder_profiles bp ON cb.builder_profile_id = bp.id
            LIMIT 5
        """)

        samples = cursor.fetchall()
        if samples:
            print(f"✅ Sample of {len(samples)} linked cards:")
            for s in samples:
                match_indicator = "✓" if s['card_name'].lower() in s['profile_name'].lower() or s['profile_name'].lower() in s['card_name'].lower() else "?"
                print(f"   {match_indicator} Card '{s['card_name']}' -> Profile '{s['profile_name']}' ({s['profile_builder_id']})")
        else:
            print("⚠️  No linked cards found to sample")

        print("\n" + "=" * 80)
        print("TEST 4: Builder ID Format Validation")
        print("=" * 80)

        # Check builder_id format in builder_profiles
        cursor.execute("""
            SELECT builder_id, name
            FROM builder_profiles
            WHERE builder_id NOT LIKE 'BLD-%'
            LIMIT 5
        """)

        invalid_formats = cursor.fetchall()
        if not invalid_formats:
            print("✅ All builder_id values follow the 'BLD-*' format")
        else:
            print(f"⚠️  Found {len(invalid_formats)} builder_id values with unexpected format:")
            for inv in invalid_formats:
                print(f"   - {inv['builder_id']} ({inv['name']})")

        # Check for unique builder_id
        cursor.execute("""
            SELECT builder_id, COUNT(*) as count
            FROM builder_profiles
            GROUP BY builder_id
            HAVING count > 1
        """)

        duplicates = cursor.fetchall()
        if not duplicates:
            print("✅ All builder_id values are unique")
        else:
            print(f"❌ Found {len(duplicates)} duplicate builder_id values:")
            for dup in duplicates:
                print(f"   - {dup['builder_id']}: {dup['count']} occurrences")

        print("\n" + "=" * 80)
        print("TEST 5: Unlinked Cards Analysis")
        print("=" * 80)

        # Get unlinked cards grouped by name
        cursor.execute("""
            SELECT name, COUNT(*) as count
            FROM community_builders
            WHERE builder_profile_id IS NULL
            GROUP BY name
            ORDER BY count DESC
            LIMIT 10
        """)

        unlinked_by_name = cursor.fetchall()
        if unlinked_by_name:
            print(f"Top 10 unlinked builder names:")
            for item in unlinked_by_name:
                print(f"   - {item['name']}: {item['count']} card(s)")
        else:
            print("✅ All builder cards are linked!")

        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        issues = []
        if len(columns) != 3:
            issues.append("Missing required columns")
        if not fk:
            issues.append("Missing foreign key constraint")
        if broken_links > 0:
            issues.append(f"{broken_links} broken links")
        if duplicates:
            issues.append(f"{len(duplicates)} duplicate builder_id values")

        if not issues:
            print("✅ ALL TESTS PASSED!")
            print("\nIntegration Status: READY FOR PRODUCTION")
        else:
            print(f"❌ Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"   - {issue}")
            print("\nIntegration Status: NEEDS ATTENTION")

        print("\nStatistics:")
        print(f"   - Total builder cards: {total_cards}")
        print(f"   - Linked: {linked_cards} ({100 * linked_cards / total_cards if total_cards > 0 else 0:.1f}%)")
        print(f"   - Unlinked: {unlinked_cards} ({100 * unlinked_cards / total_cards if total_cards > 0 else 0:.1f}%)")

finally:
    connection.close()
    print("\n✓ Database connection closed")
