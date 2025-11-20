"""
Find an admin user in the database
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
        # Find admin users
        cursor.execute("""
            SELECT user_id, email, role, first_name, last_name
            FROM users
            WHERE role = 'admin'
            LIMIT 5
        """)
        admins = cursor.fetchall()

        if admins:
            print("Admin users found:")
            print("="*80)
            for admin in admins:
                print(f"Email: {admin['email']}")
                print(f"User ID: {admin['user_id']}")
                print(f"Name: {admin.get('first_name', 'N/A')} {admin.get('last_name', 'N/A')}")
                print(f"Role: {admin['role']}")
                print("-"*80)
        else:
            print("No admin users found in database")

finally:
    connection.close()
