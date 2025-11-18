#!/usr/bin/env python3
"""
Test MinIO Connection
This script tests the connection to MinIO and creates the required bucket.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_minio_connection():
    """Test connection to MinIO and create bucket if needed"""

    print("=" * 60)
    print("MinIO Connection Test")
    print("=" * 60)
    print()

    # Get configuration from environment
    endpoint_url = os.getenv("S3_ENDPOINT_URL", "http://100.94.199.71:9000")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("S3_BUCKET_NAME", "artitec-media")
    region = os.getenv("AWS_REGION", "us-east-1")

    print(f"Endpoint: {endpoint_url}")
    print(f"Bucket: {bucket_name}")
    print(f"Region: {region}")
    print()

    if not access_key or not secret_key:
        print("⚠️  WARNING: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY not set!")
        print("   For initial testing, using MinIO root credentials...")
        access_key = "artitec-admin"
        secret_key = "ArtitecMinIO2024!SecurePassword"

    try:
        # Create S3 client
        print("1. Creating S3 client...")
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        print("   ✓ S3 client created")
        print()

        # Test connection by listing buckets
        print("2. Testing connection (listing buckets)...")
        response = s3_client.list_buckets()
        print(f"   ✓ Connection successful!")
        print(f"   Found {len(response['Buckets'])} bucket(s):")
        for bucket in response['Buckets']:
            print(f"     - {bucket['Name']}")
        print()

        # Check if our bucket exists
        print(f"3. Checking if bucket '{bucket_name}' exists...")
        bucket_exists = any(b['Name'] == bucket_name for b in response['Buckets'])

        if bucket_exists:
            print(f"   ✓ Bucket '{bucket_name}' already exists")
        else:
            print(f"   ⚠️  Bucket '{bucket_name}' does not exist")
            print(f"   Creating bucket...")
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                print(f"   ✓ Bucket '{bucket_name}' created successfully")
            except ClientError as e:
                print(f"   ❌ Error creating bucket: {e}")
                return False
        print()

        # Test upload
        print("4. Testing file upload...")
        test_content = b"Test file from Artitec Backend"
        test_key = "test/connection_test.txt"

        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=test_key,
                Body=test_content,
                ContentType='text/plain'
            )
            print(f"   ✓ Test file uploaded: {test_key}")

            # Generate URL
            file_url = f"{endpoint_url}/{bucket_name}/{test_key}"
            print(f"   URL: {file_url}")
            print()

            # Test download
            print("5. Testing file download...")
            response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
            downloaded_content = response['Body'].read()

            if downloaded_content == test_content:
                print("   ✓ File downloaded and verified successfully")
            else:
                print("   ❌ Downloaded content doesn't match uploaded content")
                return False
            print()

            # Clean up test file
            print("6. Cleaning up test file...")
            s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            print("   ✓ Test file deleted")
            print()

        except ClientError as e:
            print(f"   ❌ Error during file operations: {e}")
            return False

        # Test organized path structure
        print("7. Testing organized path structure...")
        test_paths = [
            "CMY-TEST-123/gallery/test.jpg",
            "BLD-TEST-456/profile/avatar.jpg",
            "USR-TEST-789/video/intro.mp4"
        ]

        for path in test_paths:
            try:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=path,
                    Body=b"test",
                    ContentType='application/octet-stream'
                )
                print(f"   ✓ Created: {path}")
            except ClientError as e:
                print(f"   ❌ Error creating {path}: {e}")
                return False

        # Clean up test paths
        for path in test_paths:
            s3_client.delete_object(Bucket=bucket_name, Key=path)
        print("   ✓ Test paths cleaned up")
        print()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Access MinIO Console: http://100.94.199.71:9001")
        print("2. Login: artitec-admin / ArtitecMinIO2024!SecurePassword")
        print("3. Create access keys for the application")
        print("4. Update .env with the access keys")
        print()

        return True

    except ClientError as e:
        print(f"❌ Error connecting to MinIO: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check MinIO is running: ps aux | grep minio (on NAS)")
        print("2. Check MinIO logs: tail /var/log/minio.log (on NAS)")
        print("3. Verify endpoint is accessible: curl http://100.94.199.71:9000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_minio_connection()
    sys.exit(0 if success else 1)
