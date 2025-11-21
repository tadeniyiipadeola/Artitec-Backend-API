#!/usr/bin/env python3
"""
Check builder_awards table schema to understand the mismatch
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

db_url = os.getenv("DB_URL")
engine = create_engine(db_url)

inspector = inspect(engine)

print("=== builder_awards Table Schema ===\n")

columns = inspector.get_columns("builder_awards")
print("Columns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']} {'NOT NULL' if not col['nullable'] else 'NULL'}")

print("\n=== Check if there's existing data ===")
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) as count FROM builder_awards"))
    count = result.scalar()
    print(f"Row count: {count}")

    if count > 0:
        result = conn.execute(text("SELECT * FROM builder_awards LIMIT 3"))
        print("\nSample rows:")
        for row in result:
            print(f"  {dict(row._mapping)}")
