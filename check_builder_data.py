#!/usr/bin/env python3
"""Quick script to check builder_communities data"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
db_url = os.getenv("DB_URL")

# Create engine
engine = create_engine(db_url)

print("=" * 80)
print("CHECKING BUILDER DATA")
print("=" * 80)

with engine.connect() as conn:
    # Check builder_communities table
    print("\n1. Builder Communities Association Table:")
    print("-" * 80)
    result = conn.execute(text("SELECT * FROM builder_communities LIMIT 10"))
    rows = result.fetchall()
    if rows:
        print(f"Found {len(rows)} rows (showing first 10):")
        for row in rows:
            print(f"   Builder ID: {row[0]}, Community ID: {row[1]}")
    else:
        print("❌ No data found in builder_communities table")

    # Check total count
    result = conn.execute(text("SELECT COUNT(*) as count FROM builder_communities"))
    count = result.scalar()
    print(f"\nTotal builder_communities entries: {count}")

    # Check communities table
    print("\n2. Communities Table:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT id, community_id, name
        FROM communities
        LIMIT 5
    """))
    rows = result.fetchall()
    if rows:
        print(f"Found communities (showing first 5):")
        for row in rows:
            print(f"   ID: {row[0]}, Public ID: {row[1]}, Name: {row[2]}")
    else:
        print("❌ No communities found")

    # Check builders table
    print("\n3. Builders Table:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT id, builder_id, name, is_active
        FROM builders
        LIMIT 5
    """))
    rows = result.fetchall()
    if rows:
        print(f"Found builders (showing first 5):")
        for row in rows:
            print(f"   ID: {row[0]}, Public ID: {row[1]}, Name: {row[2]}, Active: {row[3]}")
    else:
        print("❌ No builders found")

    # Check community_builders table (the legacy builder cards)
    print("\n4. Community Builders Cards Table:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT id, community_id, name, is_verified
        FROM community_builders
        LIMIT 10
    """))
    rows = result.fetchall()
    if rows:
        print(f"Found {len(rows)} builder cards (showing first 10):")
        for row in rows:
            print(f"   ID: {row[0]}, Community ID: {row[1]}, Name: {row[2]}, Verified: {row[3]}")
    else:
        print("❌ No data found in community_builders table")

    result = conn.execute(text("SELECT COUNT(*) as count FROM community_builders"))
    count = result.scalar()
    print(f"\nTotal community_builders entries: {count}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
