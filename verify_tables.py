#!/usr/bin/env python3
"""
Verify the builder extended profile tables were created successfully
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

# Load environment variables
load_dotenv()

# Get database URL
db_url = os.getenv("DB_URL")
engine = create_engine(db_url)

inspector = inspect(engine)

print("Verifying builder extended profile tables...\n")

tables_to_check = ["builder_awards", "builder_home_plans", "builder_credentials"]

for table_name in tables_to_check:
    if table_name in inspector.get_table_names():
        print(f"✓ {table_name} table exists")

        # Get columns
        columns = inspector.get_columns(table_name)
        print(f"  Columns ({len(columns)}):")
        for col in columns:
            col_info = f"    - {col['name']}: {col['type']}"
            if col.get('nullable') == False:
                col_info += " NOT NULL"
            if col.get('autoincrement'):
                col_info += " AUTO_INCREMENT"
            print(col_info)

        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print(f"  Foreign Keys ({len(fks)}):")
            for fk in fks:
                print(f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print(f"  Indexes ({len(indexes)}):")
            for idx in indexes:
                print(f"    - {idx['name']}: {idx['column_names']}")

        print()
    else:
        print(f"✗ {table_name} table NOT found")
        print()

print("Verification complete!")
