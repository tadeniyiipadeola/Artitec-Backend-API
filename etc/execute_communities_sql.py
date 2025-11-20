"""
Execute the communities bulk load SQL script
"""
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Parse DB URL
db_url = os.getenv("DB_URL")
# mysql+pymysql://Dev:Password1!@100.94.199.71:3306/appdb
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

# Read the SQL file
sql_file = "perry_homes_communities_complete_v4.sql"
print(f"Reading SQL file: {sql_file}")
with open(sql_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

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
        # Check current count
        print("\nChecking current communities count...")
        cursor.execute("SELECT COUNT(*) as count FROM communities")
        result = cursor.fetchone()
        print(f"  Current communities: {result['count']}")

        # Split SQL into individual statements
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

        print(f"\nExecuting {len([s for s in statements if s.upper().startswith('INSERT')])} INSERT statements...")

        inserted = 0
        skipped = 0

        for statement in statements:
            if statement.upper().startswith('INSERT'):
                try:
                    cursor.execute(statement)
                    inserted += 1
                    if inserted % 5 == 0:
                        print(f"  Inserted {inserted} communities...")
                except pymysql.err.IntegrityError as e:
                    # Duplicate entry or constraint violation
                    skipped += 1
                    if "Duplicate entry" in str(e):
                        pass  # Silently skip duplicates
                    else:
                        print(f"  Skipped (constraint): {e}")
                except Exception as e:
                    print(f"  Error: {e}")
                    print(f"  Statement: {statement[:100]}...")

        # Commit the transaction
        connection.commit()

        print(f"\n✓ Successfully inserted: {inserted} communities")
        if skipped > 0:
            print(f"  Skipped (duplicates/constraints): {skipped}")

        # Check final count
        cursor.execute("SELECT COUNT(*) as count FROM communities")
        result = cursor.fetchone()
        print(f"\n  Total communities in database: {result['count']}")

        # Show sample of newly inserted communities
        print("\nSample of communities in database:")
        cursor.execute("""
            SELECT name, city, state, address
            FROM communities
            ORDER BY created_at DESC
            LIMIT 5
        """)
        communities = cursor.fetchall()
        for comm in communities:
            print(f"  - {comm['name']}, {comm['city']}, {comm['state']}")
            print(f"    Address: {comm['address']}")

finally:
    connection.close()
    print("\n✓ Database connection closed")
