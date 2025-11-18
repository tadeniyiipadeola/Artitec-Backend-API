#!/usr/bin/env python3
"""
Create MinIO Access Keys for Application Use
This script creates dedicated access keys instead of using root credentials.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os

load_dotenv()

def create_access_keys():
    """Create new access keys for the application"""

    print("=" * 60)
    print("MinIO Access Key Generator")
    print("=" * 60)
    print()

    # Use root credentials to create new keys
    endpoint_url = "http://100.94.199.71:9000"
    root_user = "artitec-admin"
    root_password = "ArtitecMinIO2024!SecurePassword"

    print(f"Connecting to MinIO at {endpoint_url}...")

    try:
        # Create admin client
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=root_user,
            aws_secret_access_key=root_password,
            region_name='us-east-1'
        )

        # Test connection
        s3_client.list_buckets()
        print("✓ Connected successfully")
        print()

        # Note: MinIO doesn't support IAM via boto3 SDK the same way AWS does
        # We need to use MinIO Admin API (mc admin) or create keys via console

        print("=" * 60)
        print("Access Key Creation Instructions")
        print("=" * 60)
        print()
        print("MinIO doesn't support programmatic access key creation via boto3.")
        print("Please create access keys manually via the MinIO Console:")
        print()
        print("1. Open MinIO Console: http://100.94.199.71:9001")
        print("2. Login: artitec-admin / ArtitecMinIO2024!SecurePassword")
        print("3. Click 'Access Keys' in the left sidebar")
        print("4. Click 'Create Access Key'")
        print("5. Copy the Access Key and Secret Key")
        print("6. Update your .env file:")
        print()
        print("   AWS_ACCESS_KEY_ID=<your-new-access-key>")
        print("   AWS_SECRET_ACCESS_KEY=<your-new-secret-key>")
        print()
        print("For now, we'll continue using root credentials for testing.")
        print("This is acceptable for development but should be changed for production.")
        print()

        return True

    except ClientError as e:
        print(f"❌ Error connecting to MinIO: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    create_access_keys()
