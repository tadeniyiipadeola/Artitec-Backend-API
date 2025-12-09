#!/usr/bin/env python3
"""
Verification script for storage_type enum fix.
Run this after server restart to verify all fixes are working.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from config.db import get_db


def verify_enum_values():
    """Verify enum definitions have uppercase values"""
    print("\n" + "=" * 60)
    print("1. Verifying Enum Definitions")
    print("=" * 60)

    try:
        from model.media import StorageType as ModelStorageType
        print(f"✓ model.media.StorageType.LOCAL = '{ModelStorageType.LOCAL.value}'")
        print(f"✓ model.media.StorageType.S3 = '{ModelStorageType.S3.value}'")

        assert ModelStorageType.LOCAL.value == "LOCAL", "Model enum LOCAL should be uppercase"
        assert ModelStorageType.S3.value == "S3", "Model enum S3 should be uppercase"
        print("✅ Model enum values are correct (uppercase)")
    except Exception as e:
        print(f"❌ Model enum verification failed: {e}")
        return False

    try:
        from schema.media import StorageType as SchemaStorageType
        print(f"✓ schema.media.StorageType.LOCAL = '{SchemaStorageType.LOCAL.value}'")
        print(f"✓ schema.media.StorageType.S3 = '{SchemaStorageType.S3.value}'")

        assert SchemaStorageType.LOCAL.value == "LOCAL", "Schema enum LOCAL should be uppercase"
        assert SchemaStorageType.S3.value == "S3", "Schema enum S3 should be uppercase"
        print("✅ Schema enum values are correct (uppercase)")
    except Exception as e:
        print(f"❌ Schema enum verification failed: {e}")
        return False

    return True


def verify_database_records():
    """Verify database records use uppercase values"""
    print("\n" + "=" * 60)
    print("2. Verifying Database Records")
    print("=" * 60)

    try:
        db = next(get_db())

        # Check for lowercase values (case-sensitive)
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM media
            WHERE BINARY storage_type IN ('local', 's3')
        """))
        lowercase_count = result.scalar()

        if lowercase_count > 0:
            print(f"❌ Found {lowercase_count} records with lowercase storage_type values")
            print("   Run fix_storage_type.py to update them")
            return False
        else:
            print("✅ No lowercase storage_type values found")

        # Check uppercase distribution
        result = db.execute(text("""
            SELECT storage_type, COUNT(*) as count
            FROM media
            GROUP BY storage_type
        """))

        print("\nStorage type distribution:")
        for row in result:
            print(f"  {row.storage_type}: {row.count} records")

        # Check total
        result = db.execute(text("SELECT COUNT(*) FROM media"))
        total = result.scalar()
        print(f"\n✅ Total media records: {total}")

        return True

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False


def verify_config_normalization():
    """Verify configuration functions return uppercase values"""
    print("\n" + "=" * 60)
    print("3. Verifying Configuration Normalization")
    print("=" * 60)

    try:
        from config.media_config import MediaConfig

        config = MediaConfig.get_storage_config()
        storage_type = config['storage_type']

        print(f"✓ MediaConfig.get_storage_config()['storage_type'] = '{storage_type}'")

        assert storage_type in ['LOCAL', 'S3'], f"Storage type should be uppercase, got: {storage_type}"
        print("✅ Configuration returns uppercase storage_type")

        return True

    except Exception as e:
        print(f"❌ Configuration verification failed: {e}")
        return False


def verify_environment_variable():
    """Verify STORAGE_TYPE environment variable handling"""
    print("\n" + "=" * 60)
    print("4. Verifying Environment Variable Handling")
    print("=" * 60)

    raw_value = os.getenv('STORAGE_TYPE', 'local')
    normalized_value = os.getenv('STORAGE_TYPE', 'local').upper()

    print(f"✓ STORAGE_TYPE (raw) = '{raw_value}'")
    print(f"✓ STORAGE_TYPE (normalized) = '{normalized_value}'")

    if normalized_value not in ['LOCAL', 'S3']:
        print(f"⚠ Normalized value '{normalized_value}' is not LOCAL or S3")
        return False

    print("✅ Environment variable normalization works")
    return True


def test_media_creation():
    """Test creating a media record with uppercase enum"""
    print("\n" + "=" * 60)
    print("5. Testing Media Record Creation")
    print("=" * 60)

    try:
        from model.media import Media, StorageType, MediaType, ModerationStatus
        from config.db import get_db
        from datetime import datetime

        # Create a test media record
        test_media = Media(
            public_id="TEST-VERIFY-001",
            filename="test_verification.jpg",
            original_filename="verification.jpg",
            storage_path="test/verification.jpg",
            original_url="http://localhost:8000/uploads/test/verification.jpg",
            media_type=MediaType.IMAGE,
            storage_type=StorageType.LOCAL,  # Use enum
            file_size=1024,
            content_type="image/jpeg",
            width=100,
            height=100,
            entity_type="test",
            entity_id=1,
            entity_field="test",
            uploaded_by="TEST-USER-001",
            is_public=True,
            is_approved=True,
            moderation_status=ModerationStatus.APPROVED
        )

        print(f"✓ Created test Media instance")
        print(f"✓ storage_type value = '{test_media.storage_type.value}'")

        assert test_media.storage_type.value == "LOCAL", "Created media should have uppercase storage_type"
        print("✅ Media creation uses uppercase enum values")

        # Don't save to database - this is just a creation test
        return True

    except Exception as e:
        print(f"❌ Media creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_verifications():
    """Run all verification checks"""
    print("=" * 60)
    print("Storage Type Enum Fix - Verification Script")
    print("=" * 60)

    results = []

    # Run all verification steps
    results.append(("Enum Definitions", verify_enum_values()))
    results.append(("Database Records", verify_database_records()))
    results.append(("Configuration", verify_config_normalization()))
    results.append(("Environment Variables", verify_environment_variable()))
    results.append(("Media Creation", test_media_creation()))

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    print("=" * 60)
    print(f"Result: {passed}/{total} checks passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All verifications passed!")
        print("\nNext steps:")
        print("1. ✅ Restart the server completely (kill and restart, not auto-reload)")
        print("2. ✅ Test media scraping with a real URL")
        print("3. ✅ Test media listing endpoint (GET /v1/media/entity/community/3)")
        print("4. ✅ Verify iOS app can scrape and view media")
        return True
    else:
        print("\n⚠️  Some verifications failed. Please review the errors above.")
        print("\nTroubleshooting:")
        print("- If enum values are lowercase, the code changes didn't load properly")
        print("- If database has lowercase records, run: python fix_storage_type.py")
        print("- Make sure to restart the server completely (not just auto-reload)")
        return False


if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
