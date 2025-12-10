#!/usr/bin/env python3
"""Check if The Highlands community has any associated builders"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
db_url = os.getenv("DB_URL")

# Create engine
engine = create_engine(db_url)

print("=" * 80)
print("CHECKING THE HIGHLANDS COMMUNITY BUILDERS")
print("=" * 80)

with engine.connect() as conn:
    # First, get The Highlands community info
    print("\n1. The Highlands Community Info:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT id, community_id, name
        FROM communities
        WHERE community_id = 'CMY-1763002158-W1Y12N'
    """))
    community = result.fetchone()

    if community:
        print(f"   Internal ID: {community[0]}")
        print(f"   Public ID: {community[1]}")
        print(f"   Name: {community[2]}")
        community_internal_id = community[0]
    else:
        print("❌ The Highlands community not found!")
        exit(1)

    # Check builder_communities associations for this community
    print("\n2. Builder Associations (via builder_communities):")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT bc.builder_id, bc.community_id, b.builder_id as public_id, b.name
        FROM builder_communities bc
        JOIN builders b ON bc.builder_id = b.id
        WHERE bc.community_id = :community_id
    """), {"community_id": community_internal_id})

    builders = result.fetchall()
    if builders:
        print(f"Found {len(builders)} builders:")
        for builder in builders:
            print(f"   Builder Internal ID: {builder[0]}, Public ID: {builder[2]}, Name: {builder[3]}")
    else:
        print("❌ No builders associated with The Highlands via builder_communities table")

    # Check if there are ANY builders in the database
    print("\n3. Sample of Available Builders in Database:")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT id, builder_id, name, verified
        FROM builders
        WHERE verified = 1
        LIMIT 10
    """))
    all_builders = result.fetchall()
    if all_builders:
        print(f"Found active builders (showing first 10):")
        for builder in all_builders:
            print(f"   ID: {builder[0]}, Public ID: {builder[1]}, Name: {builder[2]}")
    else:
        print("❌ No active builders found in database")

    # Check legacy community_builders cards
    print("\n4. Legacy Builder Cards (community_builders table):")
    print("-" * 80)
    result = conn.execute(text("""
        SELECT id, name, is_verified
        FROM community_builders
        WHERE community_id = :community_public_id
    """), {"community_public_id": "CMY-1763002158-W1Y12N"})

    legacy_cards = result.fetchall()
    if legacy_cards:
        print(f"Found {len(legacy_cards)} legacy builder cards:")
        for card in legacy_cards:
            print(f"   ID: {card[0]}, Name: {card[1]}, Verified: {card[2]}")
    else:
        print("No legacy builder cards found for The Highlands")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
