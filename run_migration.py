#!/usr/bin/env python3
"""
Run the builder extended profile tables migration
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Get database URL
db_url = os.getenv("DB_URL")
if not db_url:
    raise ValueError("DB_URL not found in environment variables")

print(f"Connecting to database...")

# Create engine
engine = create_engine(db_url)

# Read migration file
migration_file = Path("migrations/create_builder_extended_profile_tables.sql")
if not migration_file.exists():
    raise FileNotFoundError(f"Migration file not found: {migration_file}")

print(f"Reading migration file: {migration_file}")
migration_sql = migration_file.read_text()

# Split by semicolons and execute each statement
statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

print(f"Executing {len(statements)} SQL statements...")

with engine.connect() as conn:
    for i, statement in enumerate(statements, 1):
        if statement:
            print(f"  [{i}/{len(statements)}] Executing statement...")
            conn.execute(text(statement))
            conn.commit()

print("✓ Migration completed successfully!")
print("  - builder_awards table created")
print("  - builder_home_plans table created")
print("  - builder_credentials table created")
