"""
Debug script to check display_name in buyer_profiles table
"""
import mysql.connector
from mysql.connector import Error

def check_buyer_profiles():
    try:
        connection = mysql.connector.connect(
            host='artitec-db.c056qovkj5wu.us-east-2.rds.amazonaws.com',
            database='artitec_db',
            user='admin',
            password='artitecdatabase123'
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            # Check table structure
            print("=" * 80)
            print("BUYER_PROFILES TABLE STRUCTURE:")
            print("=" * 80)
            cursor.execute("DESCRIBE buyer_profiles")
            columns = cursor.fetchall()
            for col in columns:
                print(f"{col['Field']:30} {col['Type']:20} {col['Null']:5} {col['Key']:5} {col['Default']}")

            # Check recent data
            print("\n" + "=" * 80)
            print("RECENT BUYER PROFILES DATA:")
            print("=" * 80)
            cursor.execute("""
                SELECT
                    id, user_id, display_name, first_name, last_name,
                    bio, email, contact_email, profile_image,
                    created_at, updated_at
                FROM buyer_profiles
                ORDER BY created_at DESC
                LIMIT 5
            """)
            profiles = cursor.fetchall()

            for prof in profiles:
                print(f"\nID: {prof['id']}, User ID: {prof['user_id']}")
                print(f"  display_name: {prof['display_name']}")
                print(f"  first_name: {prof['first_name']}, last_name: {prof['last_name']}")
                print(f"  bio: {prof['bio']}")
                print(f"  email: {prof['email']}, contact_email: {prof['contact_email']}")
                print(f"  profile_image: {prof['profile_image']}")
                print(f"  created: {prof['created_at']}, updated: {prof['updated_at']}")

            # Check if avatar_symbol column still exists
            print("\n" + "=" * 80)
            print("CHECKING FOR OLD avatar_symbol COLUMN:")
            print("=" * 80)
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'artitec_db'
                  AND TABLE_NAME = 'buyer_profiles'
                  AND COLUMN_NAME IN ('avatar_symbol', 'profile_image')
            """)
            cols = cursor.fetchall()
            for col in cols:
                print(f"  Found column: {col['COLUMN_NAME']}")

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("\n" + "=" * 80)
            print("Database connection closed.")

if __name__ == "__main__":
    check_buyer_profiles()
