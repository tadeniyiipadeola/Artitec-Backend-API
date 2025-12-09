"""
Test script for Media Management System
Run this to verify the system is set up correctly
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")

    try:
        from model.media import Media, MediaType, StorageType, ModerationStatus
        print("✓ Media model imports successful")
    except ImportError as e:
        print(f"✗ Failed to import media model: {e}")
        return False

    try:
        from schema.media import (
            MediaOut, MediaUploadRequest, MediaUpdateRequest,
            BatchUploadRequest, StorageType, ModerationStatus
        )
        print("✓ Media schemas import successful")
    except ImportError as e:
        print(f"✗ Failed to import media schemas: {e}")
        return False

    try:
        from src.media_processor import (
            MediaValidator, ImageProcessorEnhanced,
            PathGenerator, DuplicateDetector, FileHasher
        )
        print("✓ Media processor imports successful")
    except ImportError as e:
        print(f"✗ Failed to import media processor: {e}")
        return False

    try:
        from src.storage_service import MinIOStorageService, get_minio_service
        print("✓ Storage service imports successful")
    except ImportError as e:
        print(f"✗ Failed to import storage service: {e}")
        return False

    try:
        from config.media_config import MediaConfig
        print("✓ Media config imports successful")
    except ImportError as e:
        print(f"✗ Failed to import media config: {e}")
        return False

    try:
        from routes.media import entities
        print("✓ Entity routes import successful")
    except ImportError as e:
        print(f"✗ Failed to import entity routes: {e}")
        return False

    return True


def test_dependencies():
    """Test that required dependencies are installed"""
    print("\nTesting dependencies...")

    required_packages = [
        ('PIL', 'Pillow'),
        ('imagehash', 'imagehash'),
        ('boto3', 'boto3'),
    ]

    all_installed = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✓ {package_name} is installed")
        except ImportError:
            print(f"✗ {package_name} is NOT installed. Run: pip install {package_name}")
            all_installed = False

    return all_installed


def test_configuration():
    """Test configuration values"""
    print("\nTesting configuration...")

    from config.media_config import MediaConfig

    # Test file types
    assert len(MediaConfig.ALLOWED_IMAGE_TYPES) > 0
    assert len(MediaConfig.ALLOWED_VIDEO_TYPES) > 0
    print("✓ File type configurations OK")

    # Test size limits
    assert MediaConfig.MAX_IMAGE_SIZE > 0
    assert MediaConfig.MAX_VIDEO_SIZE > 0
    print("✓ Size limit configurations OK")

    # Test thumbnail sizes
    assert len(MediaConfig.IMAGE_SIZES) > 0
    print("✓ Thumbnail configurations OK")

    # Test storage config
    storage_config = MediaConfig.get_storage_config()
    assert 'storage_type' in storage_config
    print(f"✓ Storage type: {storage_config['storage_type']}")

    return True


def test_media_processor():
    """Test media processor functions"""
    print("\nTesting media processor...")

    from src.media_processor import MediaValidator, PathGenerator

    # Test file validation
    is_valid, error, media_type = MediaValidator.validate_file(
        "test.jpg",
        1024 * 1024,  # 1 MB
        "image/jpeg"
    )
    assert is_valid == True
    assert media_type == "image"
    print("✓ File validation works")

    # Test invalid file
    is_valid, error, media_type = MediaValidator.validate_file(
        "test.exe",
        1024,
        "application/exe"
    )
    assert is_valid == False
    print("✓ Invalid file detection works")

    # Test filename generation
    filename = PathGenerator.generate_unique_filename(
        "original.jpg",
        "photo"
    )
    assert filename.endswith('.jpg')
    assert 'photo-' in filename
    print(f"✓ Filename generation works: {filename}")

    # Test storage path generation
    path = PathGenerator.generate_storage_path(
        "community",
        "photos",
        "CMY-123",
        "test.jpg"
    )
    assert "communities" in path
    assert "photos" in path
    assert "CMY-123" in path
    print(f"✓ Storage path generation works: {path}")

    return True


def test_model_enums():
    """Test model enums"""
    print("\nTesting model enums...")

    from model.media import MediaType, StorageType, ModerationStatus

    # Test MediaType
    assert MediaType.IMAGE.value == "IMAGE"
    assert MediaType.VIDEO.value == "VIDEO"
    print("✓ MediaType enum OK")

    # Test StorageType
    assert StorageType.LOCAL.value == "LOCAL"
    assert StorageType.S3.value == "S3"
    print("✓ StorageType enum OK")

    # Test ModerationStatus
    assert ModerationStatus.PENDING.value == "pending"
    assert ModerationStatus.APPROVED.value == "approved"
    assert ModerationStatus.REJECTED.value == "rejected"
    assert ModerationStatus.FLAGGED.value == "flagged"
    print("✓ ModerationStatus enum OK")

    return True


def test_environment():
    """Test environment variables"""
    print("\nTesting environment variables...")

    env_vars = [
        'STORAGE_TYPE',
        'BASE_URL',
    ]

    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} = {value}")
        else:
            print(f"⚠ {var} is not set (will use default)")

    # Check MinIO-specific vars
    if os.getenv('STORAGE_TYPE', '').upper() == 'S3':
        minio_vars = [
            'S3_ENDPOINT_URL',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'S3_BUCKET_NAME',
        ]
        for var in minio_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if 'KEY' in var or 'SECRET' in var:
                    print(f"✓ {var} = {'*' * len(value)}")
                else:
                    print(f"✓ {var} = {value}")
            else:
                print(f"⚠ {var} is not set (required for S3 storage)")

    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Media Management System - Setup Verification")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Dependencies", test_dependencies),
        ("Configuration", test_configuration),
        ("Media Processor", test_media_processor),
        ("Model Enums", test_model_enums),
        ("Environment", test_environment),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test failed with error: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")

    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All tests passed! Media Management System is ready to use.")
        return True
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
