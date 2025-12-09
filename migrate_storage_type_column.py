#!/usr/bin/env python3
"""
Database migration to update storage_type ENUM column from lowercase to uppercase.
This is the CRITICAL fix - the MySQL column itself has lowercase enum values!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.db import get_db
from sqlalchemy import text


def migrate_storage_type_column():
    """Alter the storage_type column to use uppercase ENUM values"""

    print("=" * 70)
    print("Database Migration: storage_type ENUM Column")
    print("=" * 70)

    db = next(get_db())

    try:
        # Step 1: Check current column definition
        print("\n1. Checking current column definition...")
        result = db.execute(text('SHOW COLUMNS FROM media LIKE "storage_type"'))
        for row in result:
            print(f"   Current Type: {row.Type}")
            print(f"   Current Default: {row.Default}")

        # Step 2: Alter the column to use uppercase ENUM values
        print("\n2. Altering column to use uppercase ENUM values...")
        print("   This will:")
        print("   - Change ENUM('local', 's3') to ENUM('LOCAL', 'S3')")
        print("   - Change default from 'local' to 'LOCAL'")

        # MySQL will automatically convert existing values when we ALTER
        db.execute(text("""
            ALTER TABLE media
            MODIFY COLUMN storage_type
            ENUM('LOCAL', 'S3')
            NOT NULL
            DEFAULT 'LOCAL'
            COMMENT 'Storage backend: local or s3'
        """))
        db.commit()
        print("   ✅ Column altered successfully")

        # Step 3: Verify new column definition
        print("\n3. Verifying new column definition...")
        result = db.execute(text('SHOW COLUMNS FROM media LIKE "storage_type"'))
        for row in result:
            print(f"   New Type: {row.Type}")
            print(f"   New Default: {row.Default}")

        # Step 4: Check data distribution
        print("\n4. Checking data distribution...")
        result = db.execute(text("""
            SELECT storage_type, COUNT(*) as count
            FROM media
            GROUP BY storage_type
        """))

        for row in result:
            print(f"   {row.storage_type}: {row.count} records")

        # Step 5: Final validation
        print("\n5. Validating no lowercase values exist...")
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM media
            WHERE storage_type NOT IN ('LOCAL', 'S3')
        """))
        invalid_count = result.scalar()

        if invalid_count > 0:
            print(f"   ⚠️  Found {invalid_count} records with invalid storage_type values")
            return False
        else:
            print("   ✅ All records have valid uppercase storage_type values")

        print("\n" + "=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Restart the FastAPI server completely (not auto-reload)")
        print("2. Run: python verify_enum_fix.py")
        print("3. Test media scraping and listing endpoints")

        return True

    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate_storage_type_column()
    sys.exit(0 if success else 1)
