#!/usr/bin/env python3
"""
Investigate Kelle Gandy's enterprise account and builder profiles.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config.settings import DB_URL

# Create database connection
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def main():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("KELLE GANDY ENTERPRISE ACCOUNT INVESTIGATION")
        print("=" * 80)

        # 1. Find Kelle Gandy's user record
        print("\n1. FINDING KELLE GANDY'S USER RECORD")
        print("-" * 80)

        query = text("""
            SELECT user_id, email, role, plan_tier,
                   first_name, last_name, onboarding_completed,
                   created_at, status
            FROM users
            WHERE email LIKE :email_pattern
               OR first_name LIKE :name_pattern
               OR last_name LIKE :name_pattern
        """)

        result = db.execute(query, {
            'email_pattern': '%kelle%',
            'name_pattern': '%gandy%'
        })
        users = result.fetchall()

        if not users:
            print("❌ No user found matching 'Kelle Gandy'")
            print("\nSearching for Perry Homes users instead...")

            # Search for Perry Homes users
            query = text("""
                SELECT user_id, email, role, plan_tier,
                       first_name, last_name, onboarding_completed
                FROM users
                WHERE email LIKE '%perry%'
                   OR first_name LIKE '%perry%'
                LIMIT 10
            """)
            result = db.execute(query)
            perry_users = result.fetchall()

            if perry_users:
                print(f"\nFound {len(perry_users)} Perry-related users:")
                for user in perry_users:
                    print(f"\n  User ID: {user.user_id}")
                    print(f"  Email: {user.email}")
                    print(f"  Name: {user.first_name} {user.last_name}")
                    print(f"  Role: {user.role}")
                    print(f"  Plan: {user.plan_tier}")

            # Also search for enterprise users
            print("\n\nSearching for enterprise plan users...")
            query = text("""
                SELECT user_id, email, role, plan_tier,
                       first_name, last_name, onboarding_completed
                FROM users
                WHERE plan_tier = 'enterprise' OR role = 'builder'
                LIMIT 10
            """)
            result = db.execute(query)
            enterprise_users = result.fetchall()

            if enterprise_users:
                print(f"\nFound {len(enterprise_users)} enterprise/builder users:")
                for user in enterprise_users:
                    print(f"\n  User ID: {user.user_id}")
                    print(f"  Email: {user.email}")
                    print(f"  Name: {user.first_name} {user.last_name}")
                    print(f"  Role: {user.role}")
                    print(f"  Plan: {user.plan_tier}")

            return

        kelle = users[0]
        print(f"\n✅ Found Kelle Gandy:")
        print(f"   User ID: {kelle.user_id}")
        print(f"   Email: {kelle.email}")
        print(f"   Name: {kelle.first_name} {kelle.last_name}")
        print(f"   Role: {kelle.role}")
        print(f"   Plan Tier: {kelle.plan_tier}")
        print(f"   Onboarding Completed: {kelle.onboarding_completed}")
        print(f"   Status: {kelle.status}")
        print(f"   Created At: {kelle.created_at}")

        # 2. Check builder profiles owned by Kelle
        print("\n\n2. BUILDER PROFILES OWNED BY KELLE")
        print("-" * 80)

        query = text("""
            SELECT id, builder_id, name, city, state, verified,
                   website, rating, created_at
            FROM builder_profiles
            WHERE user_id = :user_id
        """)

        result = db.execute(query, {'user_id': kelle.user_id})
        owned_profiles = result.fetchall()

        print(f"\nFound {len(owned_profiles)} owned profile(s):")
        for profile in owned_profiles:
            print(f"\n  Profile ID: {profile.id}")
            print(f"  Builder ID: {profile.builder_id}")
            print(f"  Name: {profile.name}")
            print(f"  Location: {profile.city}, {profile.state}")
            print(f"  Verified: {'Yes' if profile.verified else 'No'}")
            print(f"  Rating: {profile.rating}")
            print(f"  Website: {profile.website}")

        # 3. Check team memberships
        print("\n\n3. TEAM MEMBERSHIPS FOR KELLE")
        print("-" * 80)

        query = text("""
            SELECT id, builder_id, role, permissions,
                   communities_assigned, is_active, created_at
            FROM builder_team_members
            WHERE user_id = :user_id
        """)

        result = db.execute(query, {'user_id': kelle.user_id})
        team_memberships = result.fetchall()

        print(f"\nFound {len(team_memberships)} team membership(s):")
        for membership in team_memberships:
            print(f"\n  Membership ID: {membership.id}")
            print(f"  Builder ID: {membership.builder_id}")
            print(f"  Role: {membership.role}")
            print(f"  Permissions: {membership.permissions}")
            print(f"  Communities Assigned: {membership.communities_assigned}")
            print(f"  Active: {membership.is_active}")
            print(f"  Created At: {membership.created_at}")

            # Get the builder profile for this team membership
            query2 = text("""
                SELECT id, builder_id, name, city, state, verified
                FROM builder_profiles
                WHERE builder_id = :builder_id
            """)

            result2 = db.execute(query2, {'builder_id': membership.builder_id})
            builder = result2.fetchone()

            if builder:
                print(f"  → Builder Profile: {builder.name} ({builder.city}, {builder.state})")
                print(f"     Profile ID: {builder.id}")
                print(f"     Verified: {'Yes' if builder.verified else 'No'}")

        # 4. Get all accessible profiles (owned + team memberships)
        print("\n\n4. ALL ACCESSIBLE BUILDER PROFILES")
        print("-" * 80)

        # Query for owned profiles
        query = text("""
            SELECT DISTINCT bp.id, bp.builder_id, bp.name, bp.city, bp.state,
                   bp.verified, bp.rating, bp.user_id,
                   'owned' as access_type
            FROM builder_profiles bp
            WHERE bp.user_id = :user_id

            UNION

            SELECT DISTINCT bp.id, bp.builder_id, bp.name, bp.city, bp.state,
                   bp.verified, bp.rating, bp.user_id,
                   'team_member' as access_type
            FROM builder_profiles bp
            INNER JOIN builder_team_members btm ON bp.builder_id = btm.builder_id
            WHERE btm.user_id = :user_id AND btm.is_active = 'active'

            ORDER BY name
        """)

        result = db.execute(query, {'user_id': kelle.user_id})
        all_profiles = result.fetchall()

        print(f"\n✅ Total accessible profiles: {len(all_profiles)}")
        print("\nProfile Details:")
        print("-" * 80)

        for i, profile in enumerate(all_profiles, 1):
            print(f"\n{i}. {profile.name}")
            print(f"   Profile ID: {profile.id}")
            print(f"   Builder ID: {profile.builder_id}")
            print(f"   Location: {profile.city}, {profile.state}")
            print(f"   Verified: {'Yes' if profile.verified else 'No'}")
            print(f"   Rating: {profile.rating}")
            print(f"   Access Type: {profile.access_type}")

        # 5. Check for Perry Homes profiles
        print("\n\n5. PERRY HOMES PROFILES")
        print("-" * 80)

        query = text("""
            SELECT id, builder_id, name, city, state, verified, user_id
            FROM builder_profiles
            WHERE name LIKE '%Perry%' OR name LIKE '%perry%'
        """)

        result = db.execute(query)
        perry_profiles = result.fetchall()

        print(f"\nFound {len(perry_profiles)} Perry Homes profile(s):")
        for profile in perry_profiles:
            print(f"\n  Profile ID: {profile.id}")
            print(f"  Builder ID: {profile.builder_id}")
            print(f"  Name: {profile.name}")
            print(f"  Location: {profile.city}, {profile.state}")
            print(f"  Owner User ID: {profile.user_id}")
            print(f"  Verified: {'Yes' if profile.verified else 'No'}")

            # Check if this profile is accessible to Kelle
            is_accessible = any(p.builder_id == profile.builder_id for p in all_profiles)
            print(f"  Accessible to Kelle: {'✅ Yes' if is_accessible else '❌ No'}")

        # 6. Database schema verification
        print("\n\n6. DATABASE SCHEMA VERIFICATION")
        print("-" * 80)

        # Check users table structure
        query = text("DESCRIBE users")
        result = db.execute(query)
        print("\nusers table structure:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        # Check builder_profiles table structure
        query = text("DESCRIBE builder_profiles")
        result = db.execute(query)
        print("\nbuilder_profiles table structure:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        # Check builder_team_members table structure
        query = text("DESCRIBE builder_team_members")
        result = db.execute(query)
        print("\nbuilder_team_members table structure:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        # 7. Data flow verification
        print("\n\n7. DATA FLOW VERIFICATION")
        print("-" * 80)
        print("\nThe endpoint GET /v1/profiles/builders/me/profiles should:")
        print("1. Get authenticated user's user_id from current_user.user_id")
        print("2. Query builder_profiles WHERE user_id = current_user.user_id (owned profiles)")
        print("3. Query builder_team_members WHERE user_id = current_user.user_id (team memberships)")
        print("4. For each team membership, get builder_profiles WHERE builder_id = membership.builder_id")
        print("5. Combine and deduplicate all profiles")

        print(f"\n✅ Expected profile count for Kelle: {len(all_profiles)}")
        print(f"   - Owned profiles: {len(owned_profiles)}")
        print(f"   - Team member profiles: {len(team_memberships)}")

        # 8. Check for issues
        print("\n\n8. POTENTIAL ISSUES")
        print("-" * 80)

        issues = []

        if len(all_profiles) < 18:
            issues.append(f"⚠️ Expected ~18 Perry Homes profiles, but found {len(all_profiles)} accessible to Kelle")

        if len(perry_profiles) > len(all_profiles):
            issues.append(f"⚠️ There are {len(perry_profiles)} Perry Homes profiles in database, but only {len(all_profiles)} accessible to Kelle")

        if len(owned_profiles) == 0 and len(team_memberships) == 0:
            issues.append("❌ CRITICAL: Kelle has no owned profiles and no team memberships!")

        # Check for team memberships without corresponding builder profiles
        for membership in team_memberships:
            query = text("SELECT COUNT(*) as count FROM builder_profiles WHERE builder_id = :builder_id")
            result = db.execute(query, {'builder_id': membership.builder_id})
            count = result.fetchone()[0]
            if count == 0:
                issues.append(f"❌ Team membership references non-existent builder_id: {membership.builder_id}")

        if issues:
            print("\nIssues found:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("\n✅ No issues found!")

        print("\n" + "=" * 80)
        print("INVESTIGATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
