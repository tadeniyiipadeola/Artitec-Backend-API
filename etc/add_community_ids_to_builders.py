"""
Add community_ids column to builder_profiles table to store associated community IDs
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

print("=" * 80)
print("ADDING community_ids COLUMN TO builder_profiles TABLE")
print("=" * 80)
print()

# Connect to database
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
        # Check if column already exists
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'builder_profiles'
            AND COLUMN_NAME = 'community_ids'
        """, (database,))

        existing_column = cursor.fetchone()

        if existing_column:
            print("Column 'community_ids' already exists in builder_profiles table.")
        else:
            print("Adding 'community_ids' column to builder_profiles table...")

            # Add column as JSON type to store array of community IDs
            cursor.execute("""
                ALTER TABLE builder_profiles
                ADD COLUMN community_ids JSON NULL
                AFTER communities_served
            """)

            connection.commit()
            print("✓ Column added successfully!")

        print()
        print("=" * 80)
        print("COMPLETE!")
        print("=" * 80)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    connection.rollback()

finally:
    connection.close()
