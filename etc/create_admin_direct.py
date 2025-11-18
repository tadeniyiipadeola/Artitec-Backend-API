#!/usr/bin/env python3
"""
Create Community Admin Profile using direct DB connection
"""

import time
import secrets
import pymysql
from pymysql.cursors import DictCursor

# Database configuration
DB_CONFIG = {
    'host': '100.94.199.71',
    'user': 'Dev',
    'password': 'Password1!',
    'database': 'appdb',
    'cursorclass': DictCursor
}


def generate_community_admin_id():
    """Generate community admin ID: ADM-TIMESTAMP-RANDOM"""
    timestamp = int(time.time())
    random_bytes = secrets.token_urlsafe(6)
    random_part = random_bytes.replace('-', '').replace('_', '')[:6].upper()
    return f"ADM-{timestamp}-{random_part}"


def main():
    """Create community admin profile"""
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cursor:
            # Step 1: Find the user
            print("🔍 Finding user USR-1763002155-GRZVLL...")
            cursor.execute(
                "SELECT id, user_id, email, first_name, last_name, phone_e164, role FROM users WHERE user_id = %s",
                ('USR-1763002155-GRZVLL',)
            )
            user = cursor.fetchone()

            if not user:
                print("❌ User not found")
                return

            print(f"✅ Found user: {user['first_name']} {user['last_name']}")
            print(f"   User ID: {user['user_id']}")
            print(f"   Email: {user['email']}")
            print(f"   Role: {user['role']}")

            # Step 2: Find The Highlands community
            print("\n🔍 Finding The Highlands community...")
            cursor.execute(
                "SELECT id, community_id, name, city, state FROM communities WHERE name = %s",
                ('The Highlands',)
            )
            community = cursor.fetchone()

            if not community:
                print("❌ Community not found")
                return

            print(f"✅ Found community: {community['name']}")
            print(f"   Community ID: {community['id']}")
            print(f"   Public ID: {community.get('community_id', 'N/A')}")
            print(f"   Location: {community['city']}, {community['state']}")

            # Step 3: Check if profile already exists
            print("\n🔍 Checking if community admin profile already exists...")
            cursor.execute(
                "SELECT id, community_admin_id, community_id FROM community_admin_profiles WHERE user_id = %s",
                (user['user_id'],)
            )
            existing = cursor.fetchone()

            if existing:
                print(f"⚠️  Community admin profile already exists!")
                print(f"   Profile ID: {existing['id']}")
                print(f"   Community Admin ID: {existing['community_admin_id']}")
                print(f"   Community ID: {existing['community_id']}")
                return

            # Step 4: Create new community admin profile
            print("\n📝 Creating community admin profile...")

            community_admin_id = generate_community_admin_id()

            insert_sql = """
            INSERT INTO community_admin_profiles (
                community_admin_id,
                user_id,
                community_id,
                first_name,
                last_name,
                title,
                contact_email,
                contact_phone,
                contact_preferred,
                can_post_announcements,
                can_manage_events,
                can_moderate_threads
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                insert_sql,
                (
                    community_admin_id,
                    user['user_id'],
                    community['id'],
                    user['first_name'],
                    user['last_name'],
                    'Community Admin',
                    user['email'],
                    user.get('phone_e164'),
                    'email',
                    True,
                    True,
                    True
                )
            )

            conn.commit()

            # Step 5: Verify the insert
            print("\n🔍 Verifying insert...")
            cursor.execute(
                """
                SELECT
                    cap.id,
                    cap.community_admin_id,
                    cap.user_id,
                    cap.community_id,
                    cap.first_name,
                    cap.last_name,
                    cap.title,
                    c.name as community_name
                FROM community_admin_profiles cap
                JOIN communities c ON cap.community_id = c.id
                WHERE cap.user_id = %s
                """,
                (user['user_id'],)
            )
            result = cursor.fetchone()

            if result:
                print("✅ Community admin profile created successfully!")
                print(f"\n   Profile Details:")
                print(f"   - ID: {result['id']}")
                print(f"   - Community Admin ID: {result['community_admin_id']}")
                print(f"   - User: {result['first_name']} {result['last_name']} ({result['user_id']})")
                print(f"   - Community: {result['community_name']} (ID: {result['community_id']})")
                print(f"   - Title: {result['title']}")
            else:
                print("❌ Failed to verify insert")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
