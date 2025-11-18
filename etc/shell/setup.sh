#!/bin/bash
# Artitec Backend Development - One-Command Setup Script
# This script sets up the entire development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.9"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
ENV_FILE="$PROJECT_DIR/.env"

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

# Banner
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║      Artitec Backend Development Setup          ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check Prerequisites
print_header "Step 1: Checking Prerequisites"

MISSING_DEPS=0

# Check Python
if python3 --version &> /dev/null; then
    PYTHON_VER=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VER is installed"
else
    print_error "Python 3 is not installed"
    print_info "Install Python 3: brew install python3"
    MISSING_DEPS=1
fi

# Check pip
if python3 -m pip --version &> /dev/null; then
    print_success "pip is installed"
else
    print_error "pip is not installed"
    MISSING_DEPS=1
fi

# Check MySQL/MariaDB
if check_command "mysql" || check_command "mariadb"; then
    :  # Already printed success message
else
    print_warning "MySQL/MariaDB not found"
    print_info "Install MariaDB: brew install mariadb"
    print_info "Or use existing MySQL installation"
    read -p "Continue without MySQL/MariaDB? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check git
if check_command "git"; then
    :
else
    print_warning "git not found - optional but recommended"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Missing required dependencies. Please install them and try again."
    exit 1
fi

# Step 2: Create Virtual Environment
print_header "Step 2: Setting Up Virtual Environment"

if [ -d "$VENV_DIR" ]; then
    print_warning "Virtual environment already exists"
    read -p "Recreate it? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        print_info "Deleted existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated"

# Step 3: Install Python Dependencies
print_header "Step 3: Installing Python Dependencies"

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    print_info "Installing from requirements.txt..."
    pip install --upgrade pip
    pip install -r "$PROJECT_DIR/requirements.txt"
    print_success "Python dependencies installed"
else
    print_warning "requirements.txt not found"
    print_info "Installing common dependencies..."
    pip install --upgrade pip
    pip install fastapi uvicorn sqlalchemy pymysql python-dotenv boto3 pillow imagehash requests beautifulsoup4
    print_success "Common dependencies installed"
fi

# Step 4: Configure Environment Variables
print_header "Step 4: Configuring Environment Variables"

if [ -f "$ENV_FILE" ]; then
    print_warning ".env file already exists"
    read -p "Update it with example values? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Keeping existing .env file"
    else
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%s)"
        print_info "Backed up existing .env file"
    fi
else
    print_info "Please provide configuration details:"
    echo ""

    # Database URL
    read -p "Database host [100.94.199.71]: " DB_HOST
    DB_HOST=${DB_HOST:-100.94.199.71}

    read -p "Database port [3306]: " DB_PORT
    DB_PORT=${DB_PORT:-3306}

    read -p "Database name [appdb]: " DB_NAME
    DB_NAME=${DB_NAME:-appdb}

    read -p "Database user [Dev]: " DB_USER
    DB_USER=${DB_USER:-Dev}

    read -sp "Database password [Password1!]: " DB_PASS
    echo ""
    DB_PASS=${DB_PASS:-Password1!}

    # Storage type
    echo ""
    echo "Storage type:"
    echo "  1) Local (for development)"
    echo "  2) MinIO/S3 (for production)"
    read -p "Choose [1]: " STORAGE_CHOICE
    STORAGE_CHOICE=${STORAGE_CHOICE:-1}

    if [ "$STORAGE_CHOICE" = "2" ]; then
        STORAGE_TYPE="s3"

        read -p "MinIO/S3 endpoint URL [http://100.94.199.71:9000]: " S3_ENDPOINT
        S3_ENDPOINT=${S3_ENDPOINT:-http://100.94.199.71:9000}

        read -p "S3 bucket name [artitec-media]: " S3_BUCKET
        S3_BUCKET=${S3_BUCKET:-artitec-media}

        read -p "AWS Access Key ID [artitec-admin]: " AWS_KEY
        AWS_KEY=${AWS_KEY:-artitec-admin}

        read -sp "AWS Secret Access Key [ArtitecMinIO2024!SecurePassword]: " AWS_SECRET
        echo ""
        AWS_SECRET=${AWS_SECRET:-ArtitecMinIO2024!SecurePassword}

        S3_PUBLIC_URL="${S3_ENDPOINT}/${S3_BUCKET}"
    else
        STORAGE_TYPE="local"
        S3_ENDPOINT=""
        S3_BUCKET=""
        AWS_KEY=""
        AWS_SECRET=""
        S3_PUBLIC_URL=""
    fi

    # Generate JWT secret
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(64))")
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # Create .env file
    cat > "$ENV_FILE" << EOF
# Database Configuration
DB_URL=mysql+pymysql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# JWT & Security
JWT_SECRET=${JWT_SECRET}
JWT_ALG=HS256
JWT_ISS=artitec.api
ACCESS_TTL_MIN=15
REFRESH_TTL_DAYS=30

# App Configuration
SECRET_KEY=${SECRET_KEY}
APP_ENV=development
LOG_LEVEL=INFO

# Storage Configuration
STORAGE_TYPE=${STORAGE_TYPE}

# Local Storage (Development)
UPLOAD_DIR=uploads
BASE_URL=http://127.0.0.1:8000

EOF

    if [ "$STORAGE_TYPE" = "s3" ]; then
        cat >> "$ENV_FILE" << EOF
# MinIO/S3 Storage (Production)
S3_BUCKET_NAME=${S3_BUCKET}
S3_ENDPOINT_URL=${S3_ENDPOINT}
AWS_ACCESS_KEY_ID=${AWS_KEY}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET}
AWS_REGION=us-east-1
S3_PUBLIC_BASE_URL=${S3_PUBLIC_URL}
EOF
    fi

    print_success ".env file created"
fi

# Step 5: Create Required Directories
print_header "Step 5: Creating Required Directories"

mkdir -p "$PROJECT_DIR/uploads"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/scripts"

print_success "Created uploads/, logs/, and scripts/ directories"

# Step 6: Database Setup
print_header "Step 6: Setting Up Database"

print_info "Checking database connection..."

DB_URL=$(grep "^DB_URL=" "$ENV_FILE" | cut -d'=' -f2-)

if python3 -c "
from sqlalchemy import create_engine
import sys
try:
    engine = create_engine('$DB_URL', pool_pre_ping=True)
    conn = engine.connect()
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" 2>&1; then
    print_success "Database connection verified"
else
    print_warning "Database connection failed"
    print_info "Make sure MariaDB/MySQL is running and credentials are correct"
fi

# Step 7: MinIO/S3 Setup (if using S3 storage)
if grep -q "^STORAGE_TYPE=s3" "$ENV_FILE"; then
    print_header "Step 7: Verifying MinIO/S3 Setup"

    print_info "Testing MinIO/S3 connection..."

    python3 << 'EOF'
import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

try:
    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('S3_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )

    bucket = os.getenv('S3_BUCKET_NAME')

    # Check if bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket)
        print(f'✓ Bucket "{bucket}" is accessible')
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f'⚠ Bucket "{bucket}" does not exist - creating it...')
            s3_client.create_bucket(Bucket=bucket)
            print(f'✓ Created bucket "{bucket}"')
        else:
            raise

    # Set public read policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket}/*"]
        }]
    }

    import json
    s3_client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    print(f'✓ Set public read policy on bucket')

    print('\n✓ MinIO/S3 setup complete')

except Exception as e:
    print(f'✗ MinIO/S3 setup failed: {e}', file=sys.stderr)
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_success "MinIO/S3 verified and configured"
    else
        print_warning "MinIO/S3 setup failed - check your configuration"
    fi
else
    print_header "Step 7: Storage Setup"
    print_info "Using local storage (uploads/ directory)"
    print_success "Local storage configured"
fi

# Step 8: Summary and Next Steps
print_header "Setup Complete!"

echo ""
echo -e "${GREEN}Your Artitec backend is ready to use!${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  • Project directory: $PROJECT_DIR"
echo "  • Virtual environment: $VENV_DIR"
echo "  • Storage type: $(grep '^STORAGE_TYPE=' "$ENV_FILE" | cut -d'=' -f2)"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  1. Start the development server:"
echo -e "     ${GREEN}source $VENV_DIR/bin/activate${NC}"
echo -e "     ${GREEN}python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000${NC}"
echo ""
echo "  2. Or use the quick start script:"
echo -e "     ${GREEN}./scripts/start_dev.sh${NC}"
echo ""
echo "  3. Access the API:"
echo "     http://127.0.0.1:8000"
echo "     http://127.0.0.1:8000/docs (API documentation)"
echo ""
echo "  4. Run orphan cleanup (optional):"
echo -e "     ${GREEN}python -m src.cleanup_orphans --dry-run${NC}"
echo ""
echo "  5. Setup cron job for orphan cleanup (optional):"
echo -e "     ${GREEN}./scripts/setup_orphan_cleanup_cron.sh${NC}"
echo ""
echo -e "${BLUE}Troubleshooting:${NC}"
echo "  • Logs: $PROJECT_DIR/logs/"
echo "  • Environment: $ENV_FILE"
echo "  • Database: Check config/db.py"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
echo ""
