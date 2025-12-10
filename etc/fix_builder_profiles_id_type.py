"""
Migration: Fix builder_profiles.id column type to BIGINT UNSIGNED to match model
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
        print("Checking current builder_profiles.id column type...")
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = 'id'
        """, (database,))

        col_info = cursor.fetchone()
        if col_info:
            print(f"  Current type: {col_info['COLUMN_TYPE']}")
            print(f"  Key: {col_info['COLUMN_KEY']}")
            print(f"  Extra: {col_info['EXTRA']}")
        else:
            print("  ERROR: id column not found!")
            exit(1)

        # Check if already BIGINT UNSIGNED
        if 'bigint' in col_info['COLUMN_TYPE'].lower() and 'unsigned' in col_info['COLUMN_TYPE'].lower():
            print("\n✓ Column is already BIGINT UNSIGNED, no changes needed!")
            exit(0)

        print("\nModifying builder_profiles.id to BIGINT UNSIGNED...")
        print("  This will preserve all existing data while changing the column type.")

        # Alter the column type
        # Note: We must include AUTO_INCREMENT but not PRIMARY KEY (already defined)
        cursor.execute("""
            ALTER TABLE builder_profiles
            MODIFY COLUMN id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT
        """)

        connection.commit()
        print("  ✓ Successfully modified builder_profiles.id to BIGINT UNSIGNED")

        # Verify the change
        print("\nVerifying the change...")
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = 'id'
        """, (database,))

        col_info = cursor.fetchone()
        if col_info:
            print(f"  New type: {col_info['COLUMN_TYPE']}")
            print(f"  Key: {col_info['COLUMN_KEY']}")
            print(f"  Extra: {col_info['EXTRA']}")

        # Check if any data was lost
        cursor.execute("SELECT COUNT(*) as count FROM builder_profiles")
        count = cursor.fetchone()['count']
        print(f"\n✓ Verified: {count} builder profiles still exist")

        print("\n✓ Migration complete!")

finally:
    connection.close()
    print("\n✓ Database connection closed")
