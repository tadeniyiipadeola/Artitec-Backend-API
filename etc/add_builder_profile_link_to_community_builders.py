"""
Migration: Add builder_profile_id, created_at, and updated_at columns to community_builders table
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
            AND TABLE_NAME = 'community_builders'
        """, (database,))

        existing_columns = {row['COLUMN_NAME'] for row in cursor.fetchall()}
        print(f"  Found {len(existing_columns)} existing columns")

        # Define new columns to add
        # Note: Using INT to match builder_profiles.id type (not BIGINT UNSIGNED as in model)
        columns_to_add = {
            'builder_profile_id': """ALTER TABLE community_builders
                ADD COLUMN builder_profile_id INT AFTER community_id,
                ADD INDEX idx_builder_profile_id (builder_profile_id),
                ADD CONSTRAINT fk_community_builder_profile
                    FOREIGN KEY (builder_profile_id)
                    REFERENCES builder_profiles(id)
                    ON DELETE SET NULL""",
            'created_at': """ALTER TABLE community_builders
                ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP""",
            'updated_at': """ALTER TABLE community_builders
                ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"""
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
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'community_builders'
            ORDER BY ORDINAL_POSITION
        """, (database,))

        final_columns = cursor.fetchall()
        if final_columns:
            print("  All columns in community_builders table:")
            for col in final_columns:
                nullable = "NULL" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
                default = f"DEFAULT {col['COLUMN_DEFAULT']}" if col['COLUMN_DEFAULT'] else ""
                print(f"    - {col['COLUMN_NAME']}: {col['COLUMN_TYPE']} {nullable} {default}")
        else:
            print("  WARNING: No columns found!")

        # Verify foreign key constraint
        print("\nVerifying foreign key constraint...")
        cursor.execute("""
            SELECT
                CONSTRAINT_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'community_builders'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (database,))

        foreign_keys = cursor.fetchall()
        if foreign_keys:
            print("  Foreign key constraints:")
            for fk in foreign_keys:
                print(f"    - {fk['CONSTRAINT_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")
        else:
            print("  WARNING: No foreign keys found!")

finally:
    connection.close()
    print("\n✓ Database connection closed")
