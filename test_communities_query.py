#!/usr/bin/env python3
"""Direct test of the communities query"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model.profiles.community import Community
from model.profiles.property import Property
from model.profiles.builder import BuilderProfile, builder_communities
from sqlalchemy import select, func as sql_func

load_dotenv()
engine = create_engine(os.getenv('DB_URL'))
Session = sessionmaker(bind=engine)
db = Session()

try:
    # Get a builder
    builder = db.query(BuilderProfile).filter(
        BuilderProfile.builder_id == 'BLD-1763445328-CZBQ4W'
    ).first()

    if not builder:
        print("✗ Builder not found")
    else:
        print(f"✓ Builder found: {builder.name} (id={builder.id})")

        # Try the query
        print("\nExecuting communities query...")
        stmt = select(
            Community,
            sql_func.count(Property.id).label("property_count")
        ).join(
            builder_communities,
            builder_communities.c.community_id == Community.id
        ).outerjoin(
            Property,
            (Property.community_id == Community.community_id) &
            (Property.builder_id == builder.builder_id)
        ).where(
            builder_communities.c.builder_id == builder.id
        ).group_by(Community.id)

        results = db.execute(stmt).all()

        print(f"✓ Query executed successfully")
        print(f"✓ Found {len(results)} communities")

        for community, prop_count in results:
            print(f"  - {community.name}: {prop_count} properties")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
