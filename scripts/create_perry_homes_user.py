"""
Script to create Kelle Gandy's user account and associate it with all Perry Homes builder profiles
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db import get_db
from sqlalchemy import text
import uuid
import bcrypt
from datetime import datetime, timezone

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def main():
    # User information
    email = "kelle.gandy@perryhomes.com"
    first_name = "Kelle"
    last_name = "Gandy"
    phone = "+17139487700"  # 713-948-7700
    password = "PerryHomes2025!"  # Temporary password - she should change on first login

    db = next(get_db())

    try:
        # 1. Check if user already exists
        result = db.execute(
            text("SELECT user_id, email FROM users WHERE email = :email"),
            {"email": email}
        ).fetchone()

        if result:
            user_id = result[0]
            print(f"✅ User already exists: {result[1]} (user_id: {user_id})")
        else:
            # 2. Create new user
            user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"
            hashed_pw = hash_password(password)

            # Insert user record
            db.execute(
                text("""
                    INSERT INTO users (
                        user_id, email, first_name, last_name,
                        phone_e164, role, status, is_email_verified, onboarding_completed,
                        created_at, updated_at
                    ) VALUES (
                        :user_id, :email, :first_name, :last_name,
                        :phone_e164, :role, :status, :is_email_verified, :onboarding_completed,
                        NOW(), NOW()
                    )
                """),
                {
                    "user_id": user_id,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone_e164": phone,
                    "role": "builder",
                    "status": "active",
                    "is_email_verified": True,
                    "onboarding_completed": True
                }
            )

            # Get the internal user id
            user_internal_id = db.execute(
                text("SELECT id FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).scalar()

            # Insert user_credentials record
            db.execute(
                text("""
                    INSERT INTO user_credentials (user_id, password_hash, last_password_change)
                    VALUES (:user_id, :password_hash, NOW())
                """),
                {
                    "user_id": user_internal_id,
                    "password_hash": hashed_pw
                }
            )

            print(f"✅ Created new user: {email}")
            print(f"   User ID: {user_id}")
            print(f"   Temporary Password: {password}")
            print(f"   Phone: {phone}")

        # 3. Find all Perry Homes builder profiles
        perry_profiles = db.execute(
            text("SELECT id, builder_id, name, city, state, user_id FROM builder_profiles WHERE name LIKE '%Perry%'")
        ).fetchall()

        print(f"\n📊 Found {len(perry_profiles)} Perry Homes builder profiles:")

        # 4. Update each profile to use Kelle's user_id
        updated_count = 0
        for profile in perry_profiles:
            profile_id, builder_id, name, city, state, old_user_id = profile

            db.execute(
                text("""
                    UPDATE builder_profiles
                    SET user_id = :new_user_id, updated_at = NOW()
                    WHERE id = :profile_id
                """),
                {
                    "new_user_id": user_id,
                    "profile_id": profile_id
                }
            )

            print(f"   - {name} (ID: {builder_id})")
            print(f"     Old user_id: {old_user_id} → New user_id: {user_id}")

            updated_count += 1

        # 5. Commit all changes
        db.commit()

        print(f"\n✅ SUCCESS! Updated {updated_count} builder profiles")
        print(f"\n📧 Kelle Gandy ({email}) now has access to all Perry Homes builder profiles")
        print(f"\nNext steps:")
        print(f"1. Email Kelle with her login credentials:")
        print(f"   - Email: {email}")
        print(f"   - Temporary Password: {password}")
        print(f"2. Ask her to change her password on first login")
        print(f"3. She will see a profile switcher to access all Perry Homes locations")

        # List all profiles she now has access to
        print(f"\n🏢 Perry Homes profiles now accessible:")
        for profile in perry_profiles:
            _, builder_id, name, city, state, _ = profile
            location = f"{city}, {state}" if city and state else "Location TBD"
            print(f"   • {name} - {location}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0

if __name__ == "__main__":
    exit(main())
