#!/usr/bin/env python3
"""Run the media table enhancement migration"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_url = os.getenv("DB_URL")
if not db_url:
    raise ValueError("DB_URL not found in environment variables")

print(f"Connecting to database...")
engine = create_engine(db_url)

migration_file = Path("migrations/enhance_media_table.sql")
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
            try:
                conn.execute(text(statement))
                conn.commit()
                print(f"    ✓ Success")
            except Exception as e:
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    print(f"    ⚠️  Column already exists, skipping...")
                else:
                    print(f"    ✗ Error: {e}")
                    raise

print("\n✅ Migration completed successfully!")
print("Enhanced media table with new columns:")
print("  - storage_type")
print("  - bucket_name")
print("  - is_primary")
print("  - tags (JSON)")
print("  - metadata (JSON)")
print("  - moderation_status")
