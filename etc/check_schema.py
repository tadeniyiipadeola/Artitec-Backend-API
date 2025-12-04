#!/usr/bin/env python3
"""
Check existing database schema for builder_profiles table
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

# Load environment variables
load_dotenv()

# Get database URL
db_url = os.getenv("DB_URL")
engine = create_engine(db_url)

print("Checking database schema...\n")

with engine.connect() as conn:
    # Check if builder_profiles table exists
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"Available tables ({len(tables)}):")
    for table in sorted(tables):
        print(f"  - {table}")

    if "builder_profiles" in tables:
        print("\n✓ builder_profiles table exists")

        # Get column details
        columns = inspector.get_columns("builder_profiles")
        print("\nColumns in builder_profiles:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']} {'(PK)' if col.get('primary_key') else ''}")

        # Get primary key
        pk = inspector.get_pk_constraint("builder_profiles")
        print(f"\nPrimary Key: {pk}")

        # Check existing foreign keys
        fks = inspector.get_foreign_keys("builder_profiles")
        if fks:
            print(f"\nForeign Keys: {fks}")
    else:
        print("\n✗ builder_profiles table NOT found")
        print("\nSearching for similar tables:")
        for table in tables:
            if "builder" in table.lower():
                print(f"  - {table}")
