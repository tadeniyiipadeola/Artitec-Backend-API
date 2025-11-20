"""
Migration: Add address, latitude, longitude, and total_acres columns to communities table
"""
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Parse DB URL
db_url = os.getenv("DB_URL")
parts = db_url.replace("mysql+pymysql://", "").split("@")
user_pass = parts[0].split(":")
user = user_pass[0]
password = user_pass[1]
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")
host = host_port[0]
port = int(host_port[1])
database = host_port_db[1]

print(f"Connecting to database:")
print(f"  Host: {host}")
print(f"  Port: {port}")
print(f"  Database: {database}")
print(f"  User: {user}")
print()

# Connect to database
print("Connecting to database...")
connection = pymysql.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        print("Checking existing columns...")
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'communities'
        """, (database,))

        existing_columns = {row['COLUMN_NAME'] for row in cursor.fetchall()}
        print(f"  Found {len(existing_columns)} existing columns")

        # Define new columns to add
        columns_to_add = {
            'address': "ALTER TABLE communities ADD COLUMN address VARCHAR(512) AFTER postal_code",
            'total_acres': "ALTER TABLE communities ADD COLUMN total_acres FLOAT AFTER address",
            'latitude': "ALTER TABLE communities ADD COLUMN latitude FLOAT AFTER total_acres",
            'longitude': "ALTER TABLE communities ADD COLUMN longitude FLOAT AFTER latitude"
        }

        # Add missing columns
        added = 0
        for column_name, alter_statement in columns_to_add.items():
            if column_name not in existing_columns:
                print(f"\nAdding column '{column_name}'...")
                try:
                    cursor.execute(alter_statement)
                    connection.commit()
                    print(f"  ✓ Successfully added '{column_name}'")
                    added += 1
                except Exception as e:
                    print(f"  ✗ Error adding '{column_name}': {e}")
            else:
                print(f"  • Column '{column_name}' already exists, skipping")

        print(f"\n✓ Migration complete: {added} columns added")

        # Verify final schema
        print("\nVerifying final schema...")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'communities'
            AND COLUMN_NAME IN ('address', 'total_acres', 'latitude', 'longitude')
            ORDER BY ORDINAL_POSITION
        """, (database,))

        final_columns = cursor.fetchall()
        if final_columns:
            print("  New columns in communities table:")
            for col in final_columns:
                print(f"    - {col['COLUMN_NAME']}: {col['COLUMN_TYPE']}")
        else:
            print("  WARNING: No new columns found!")

finally:
    connection.close()
    print("\n✓ Database connection closed")
