"""
Create admin links with correct schema (no role/is_active columns).
Links Fred users to The Highlands community.
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
        print("STEP 1: Find Fred users with community_admin role")
        print("="*80)

        result = session.execute(text("""
            SELECT id, user_id, email, first_name, last_name
            FROM users
            WHERE role = 'community_admin'
            ORDER BY id
        """))

        users = result.fetchall()
        print(f"\n✅ Found {len(users)} users:")
        for user in users:
            print(f"  - {user.first_name} {user.last_name} ({user.email}) [ID: {user.id}, user_id: {user.user_id}]")

        print("\n" + "="*80)
        print("STEP 2: Find The Highlands community")
        print("="*80)

        result = session.execute(text("""
            SELECT id, community_id, name
            FROM communities
            WHERE name LIKE '%Highlands%'
        """))

        highlands = result.fetchone()
        if not highlands:
            print("❌ The Highlands community not found")
            return

        print(f"✅ Found: {highlands.name} (ID: {highlands.id}, community_id: {highlands.community_id})")

        print("\n" + "="*80)
        print("STEP 3: Create admin links (simplified schema)")
        print("="*80)

        for user in users:
            # Check if link already exists
            check = session.execute(text("""
                SELECT id FROM community_admin_links
                WHERE community_id = :cid AND user_id = :uid
            """), {"cid": highlands.id, "uid": user.id})

            if check.fetchone():
                print(f"  ⚠️  {user.first_name} {user.last_name} already linked")
                continue

            print(f"\n➕ Linking {user.first_name} {user.last_name} to {highlands.name}")

            session.execute(text("""
                INSERT INTO community_admin_links
                (community_id, user_id, created_at, updated_at)
                VALUES (:cid, :uid, NOW(), NOW())
            """), {
                "cid": highlands.id,
                "uid": user.id
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
                u.role
            FROM community_admin_links cal
            JOIN communities c ON cal.community_id = c.id
            JOIN users u ON cal.user_id = u.id
            ORDER BY c.id, cal.id
        """))

        links = result.fetchall()
        print(f"\n✅ Total admin links: {len(links)}")
        for link in links:
            print(f"  ✅ {link.user_name} ({link.role}) - admin of {link.community_name}")
            print(f"     Email: {link.email}, user_id: {link.user_id}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()
