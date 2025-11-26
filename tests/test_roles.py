from sqlalchemy import create_engine, text
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://artitecUser:Qwerty!23456@127.0.0.1:3306/artitecDB")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Get all distinct role values with counts
    result = conn.execute(text("""
        SELECT 
            role,
            COUNT(*) as count,
            GROUP_CONCAT(email SEPARATOR ', ') as emails
        FROM users 
        GROUP BY role 
        ORDER BY count DESC
    """))
    
    print("All roles in users table:")
    print("=" * 80)
    total = 0
    for row in result:
        role_display = row.role if row.role else '(NULL/empty)'
        print(f"Role: {role_display:20} Count: {row.count:3}  Users: {row.emails}")
        total += row.count
    print("=" * 80)
    print(f"Total users: {total}")
