#!/usr/bin/env python3
"""Fix lowercase storage_type values in media table"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.db import get_db
from model.media import Media
from sqlalchemy import text

def main():
    db = next(get_db())

    try:
        # Find all media with lowercase storage_type using raw SQL
        result = db.execute(text("SELECT COUNT(*) FROM media WHERE storage_type = 'local'"))
        count = result.scalar()
        print(f"Found {count} media records with lowercase 'local' storage_type")

        if count > 0:
            # Update to uppercase
            db.execute(text("UPDATE media SET storage_type = 'LOCAL' WHERE storage_type = 'local'"))
            db.commit()
            print(f"✅ Updated {count} media records: 'local' -> 'LOCAL'")
        else:
            print("✅ No lowercase storage_type values found")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
