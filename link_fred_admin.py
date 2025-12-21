"""
Link existing user 'Fred' as admin to The Highlands community
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DB_URL = "mysql+pymysql://Dev:Password1!@100.94.199.71:3306/appdb"
engine = create_engine(DB_URL, echo=True)
Session = sessionmaker(bind=engine)

def main():
    session = Session()

    try:
        print("\n" + "="*80)
        print("STEP 1: Find users with role 'community_admin'")
        print("="*80)

        # Find users with community_admin role
        result = session.execute(text("""
            SELECT
                u.id,
                u.user_id,
                u.email,
                u.first_name,
                u.last_name,
                r.name as role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE r.key = 'community_admin'
            ORDER BY u.id
        """))

        users = result.fetchall()

        if not users:
            print("❌ No users found with community_admin role")
            print("   Checking all users instead...")

            result = session.execute(text("""
                SELECT
                    u.id,
                    u.user_id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    r.name as role_name
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.id
                ORDER BY u.id
            """))
            users = result.fetchall()

        print(f"\n✅ Found {len(users)} users:")
        for user in users:
            print(f"  - {user.first_name} {user.last_name} ({user.email}) - {user.role_name} [ID: {user.id}, user_id: {user.user_id}]")

        print("\n" + "="*80)
        print("STEP 2: Find The Highlands community")
        print("="*80)

        result = session.execute(text("""
            SELECT id, community_id, name
            FROM communities
            WHERE name LIKE '%Highlands%'
            ORDER BY id
        """))

        communities = result.fetchall()

        if not communities:
            print("❌ No community found with 'Highlands' in name")
            return

        highlands = communities[0]
        print(f"✅ Found: {highlands.name} (ID: {highlands.id}, community_id: {highlands.community_id})")

        if not users:
            print("\n❌ Cannot proceed - no users to link")
            return

        print("\n" + "="*80)
        print("STEP 3: Create admin links for users")
        print("="*80)

        # Link each community_admin user to The Highlands
        for user in users:
            # Check if link already exists
            check = session.execute(text("""
                SELECT id FROM community_admin_links
                WHERE community_id = :community_id AND user_id = :user_id
            """), {"community_id": highlands.id, "user_id": user.id})

            if check.fetchone():
                print(f"  ⚠️  {user.first_name} {user.last_name} already linked")
                continue

            print(f"\n➕ Linking {user.first_name} {user.last_name} to {highlands.name}")

            session.execute(text("""
                INSERT INTO community_admin_links
                (community_id, user_id, role, is_active, created_at, updated_at)
                VALUES
                (:community_id, :user_id, 'owner', 1, NOW(), NOW())
            """), {
                "community_id": highlands.id,
                "user_id": user.id
            })

        session.commit()

        print("\n" + "="*80)
        print("✅ COMPLETE - Verify admin links")
        print("="*80)

        result = session.execute(text("""
            SELECT
                cal.id,
                c.community_id,
                c.name as community_name,
                u.user_id,
                u.email,
                CONCAT(u.first_name, ' ', u.last_name) as user_name,
                r.name as role_name,
                cal.role as admin_role,
                cal.is_active
            FROM community_admin_links cal
            JOIN communities c ON cal.community_id = c.id
            JOIN users u ON cal.user_id = u.id
            LEFT JOIN roles r ON u.role_id = r.id
            ORDER BY c.id, cal.id
        """))

        links = result.fetchall()
        print(f"\n✅ Total admin links: {len(links)}")
        for link in links:
            status = "✅" if link.is_active else "❌"
            print(f"{status} {link.user_name} ({link.role_name}) - {link.admin_role} of {link.community_name}")
            print(f"   Email: {link.email}, user_id: {link.user_id}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
