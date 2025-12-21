"""
Migrate existing community_admins to community_admin_links table.
This script:
1. Reads existing admins from community_admins table
2. Finds or creates matching users
3. Creates admin links in community_admin_links table
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
        print("STEP 1: View existing community_admins")
        print("="*80)

        # Query existing community admins
        result = session.execute(text("""
            SELECT
                ca.id,
                ca.community_id,
                ca.name,
                ca.role,
                ca.email,
                ca.phone,
                c.id as community_numeric_id,
                c.community_id as community_public_id,
                c.name as community_name
            FROM community_admins ca
            JOIN communities c ON ca.community_id = c.community_id
            ORDER BY c.id, ca.id
        """))

        admins = result.fetchall()

        if not admins:
            print("❌ No admins found in community_admins table")
            return

        print(f"\n✅ Found {len(admins)} admins:")
        for admin in admins:
            print(f"  - {admin.name} ({admin.email}) - {admin.role} at {admin.community_name}")

        print("\n" + "="*80)
        print("STEP 2: Check for matching users in users table")
        print("="*80)

        migrations = []

        for admin in admins:
            print(f"\n📧 Looking for user with email: {admin.email}")

            # Try to find user by email
            user_result = session.execute(text("""
                SELECT id, user_id, email, first_name, last_name
                FROM users
                WHERE email = :email
            """), {"email": admin.email})

            user = user_result.fetchone()

            if user:
                print(f"  ✅ Found user: {user.first_name} {user.last_name} (ID: {user.id}, user_id: {user.user_id})")

                # Check if link already exists
                check_result = session.execute(text("""
                    SELECT id FROM community_admin_links
                    WHERE community_id = :community_id AND user_id = :user_id
                """), {
                    "community_id": admin.community_numeric_id,
                    "user_id": user.id
                })

                existing = check_result.fetchone()

                if existing:
                    print(f"  ⚠️  Admin link already exists (ID: {existing.id})")
                else:
                    migrations.append({
                        'community_id': admin.community_numeric_id,
                        'community_name': admin.community_name,
                        'user_id': user.id,
                        'user_public_id': user.user_id,
                        'user_name': f"{user.first_name} {user.last_name}",
                        'email': user.email,
                        'role': 'owner' if 'president' in admin.role.lower() else 'moderator'
                    })
            else:
                print(f"  ❌ No user found with email {admin.email}")
                print(f"     You'll need to create a user account for this admin first")

        if not migrations:
            print("\n⚠️  No new migrations needed - all admins either already linked or don't have user accounts")
            return

        print("\n" + "="*80)
        print(f"STEP 3: Create {len(migrations)} admin links")
        print("="*80)

        for m in migrations:
            print(f"\n➕ Creating admin link:")
            print(f"   Community: {m['community_name']} (ID: {m['community_id']})")
            print(f"   User: {m['user_name']} ({m['user_public_id']})")
            print(f"   Role: {m['role']}")

            session.execute(text("""
                INSERT INTO community_admin_links
                (community_id, user_id, role, is_active, created_at, updated_at)
                VALUES
                (:community_id, :user_id, :role, 1, NOW(), NOW())
            """), {
                "community_id": m['community_id'],
                "user_id": m['user_id'],
                "role": m['role']
            })

        # Commit all changes
        session.commit()

        print("\n" + "="*80)
        print("✅ MIGRATION COMPLETE")
        print("="*80)
        print(f"\n✨ Successfully created {len(migrations)} admin links!")

        # Verify
        print("\n" + "="*80)
        print("VERIFICATION: Current admin links")
        print("="*80)

        verify_result = session.execute(text("""
            SELECT
                cal.id,
                c.community_id,
                c.name as community_name,
                u.user_id,
                u.email,
                CONCAT(u.first_name, ' ', u.last_name) as user_name,
                cal.role,
                cal.is_active
            FROM community_admin_links cal
            JOIN communities c ON cal.community_id = c.id
            JOIN users u ON cal.user_id = u.id
            ORDER BY c.id, cal.id
        """))

        links = verify_result.fetchall()
        print(f"\n📊 Total admin links: {len(links)}")
        for link in links:
            status = "✅ Active" if link.is_active else "❌ Inactive"
            print(f"  {status} - {link.user_name} ({link.email}) is {link.role} of {link.community_name}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
