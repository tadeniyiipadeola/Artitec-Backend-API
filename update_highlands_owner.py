#!/usr/bin/env python3
"""
Update The Highlands community with user_id owner.
Connects The Highlands community to Fred Caldwell (USR-1763002155-GRZVLL).
"""

from config.db import SessionLocal
from sqlalchemy import text

def main():
    print("=" * 60)
    print("Update The Highlands Community Owner")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        # Find the user's integer ID
        print("🔍 Looking for user USR-1763002155-GRZVLL...")
        result = db.execute(text('''
            SELECT id, public_id, email, first_name, last_name
            FROM users
            WHERE public_id = :public_id
        '''), {'public_id': 'USR-1763002155-GRZVLL'})

        user = result.fetchone()
        if not user:
            print('❌ User not found with public_id: USR-1763002155-GRZVLL')
            print()
            print("Available users:")
            result = db.execute(text('''
                SELECT public_id, email, first_name, last_name
                FROM users
                LIMIT 10
            '''))
            for row in result:
                print(f"  - {row[0]}: {row[2]} {row[3]} ({row[1]})")
            return 1

        print('✅ Found user:')
        print(f'   ID: {user[0]}')
        print(f'   Public ID: {user[1]}')
        print(f'   Email: {user[2]}')
        print(f'   Name: {user[3]} {user[4]}')
        print()

        # Find The Highlands community
        print("🔍 Looking for The Highlands community...")
        result = db.execute(text('''
            SELECT id, public_id, name, user_id
            FROM communities
            WHERE name LIKE :name
            LIMIT 1
        '''), {'name': '%Highlands%'})

        community = result.fetchone()
        if not community:
            print('❌ Community not found matching "Highlands"')
            print()
            print("Available communities:")
            result = db.execute(text('''
                SELECT id, public_id, name
                FROM communities
                LIMIT 10
            '''))
            for row in result:
                print(f"  - {row[0]}: {row[2]} ({row[1]})")
            return 1

        print('✅ Found community:')
        print(f'   ID: {community[0]}')
        print(f'   Public ID: {community[1]}')
        print(f'   Name: {community[2]}')
        print(f'   Current user_id: {community[3] or "None"}')
        print()

        # Check if already updated
        if community[3] == user[0]:
            print('ℹ️  Community already owned by this user!')
            print(f'   {community[2]} is already owned by {user[3]} {user[4]}')
            return 0

        # Update the community
        print("💾 Updating community owner...")
        result = db.execute(text('''
            UPDATE communities
            SET user_id = :user_id
            WHERE id = :community_id
        '''), {'user_id': user[0], 'community_id': community[0]})

        db.commit()

        # Verify the update
        result = db.execute(text('''
            SELECT user_id FROM communities WHERE id = :community_id
        '''), {'community_id': community[0]})

        updated_user_id = result.scalar()

        print()
        print("=" * 60)
        print('✅ SUCCESS!')
        print("=" * 60)
        print(f'Community: "{community[2]}"')
        print(f'Owner: {user[3]} {user[4]}')
        print(f'Email: {user[2]}')
        print(f'User ID: {user[0]} (public_id: {user[1]})')
        print(f'Verified in database: user_id = {updated_user_id}')
        print()
        print("You can now fetch this community via:")
        print(f"  GET /api/v1/profiles/communities/{community[0]}")
        print(f"  GET /api/v1/profiles/communities/for-user/{user[1]}")
        print("=" * 60)

        return 0

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Make sure MySQL is running:")
        print("  brew services start mysql")
        print("  # OR")
        print("  mysql.server start")
        print("=" * 60)
        return 1

    finally:
        db.close()

if __name__ == "__main__":
    exit(main())
