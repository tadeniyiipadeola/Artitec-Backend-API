#!/bin/bash
# backup_db.sh
# Database backup script for Artitec Backend
# Run this BEFORE applying any migrations to protect your data

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Artitec Database Backup Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Load .env file to get DB credentials
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Extract database credentials from DB_URL
# Format: mysql+pymysql://user:password@host:port/database
if [ -z "$DB_URL" ]; then
    echo -e "${RED}Error: DB_URL not found in .env${NC}"
    exit 1
fi

# Parse DB_URL
DB_USER=$(echo $DB_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo $DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
DB_HOST=$(echo $DB_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo $DB_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo $DB_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

echo -e "\n${YELLOW}Database Info:${NC}"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"

# Create backups directory if it doesn't exist
BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR

# Generate backup filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/artitec_backup_${TIMESTAMP}.sql"

echo -e "\n${YELLOW}Starting backup...${NC}"
echo "  Backup file: $BACKUP_FILE"

# Run mysqldump
mysqldump -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS $DB_NAME > $BACKUP_FILE

if [ $? -eq 0 ]; then
    # Get file size
    FILE_SIZE=$(ls -lh $BACKUP_FILE | awk '{print $5}')

    echo -e "\n${GREEN}✅ Backup completed successfully!${NC}"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $FILE_SIZE"

    # Compress the backup
    echo -e "\n${YELLOW}Compressing backup...${NC}"
    gzip $BACKUP_FILE
    COMPRESSED_SIZE=$(ls -lh ${BACKUP_FILE}.gz | awk '{print $5}')

    echo -e "${GREEN}✅ Backup compressed!${NC}"
    echo "  File: ${BACKUP_FILE}.gz"
    echo "  Compressed size: $COMPRESSED_SIZE"

    # Keep only last 10 backups
    BACKUP_COUNT=$(ls -1 $BACKUP_DIR/*.sql.gz 2>/dev/null | wc -l)
    if [ $BACKUP_COUNT -gt 10 ]; then
        echo -e "\n${YELLOW}Cleaning up old backups (keeping last 10)...${NC}"
        ls -t $BACKUP_DIR/*.sql.gz | tail -n +11 | xargs rm -f
        echo -e "${GREEN}✅ Old backups cleaned up${NC}"
    fi

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Backup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\nYou can now safely run migrations."
    echo -e "To restore this backup if needed:"
    echo -e "  ${YELLOW}gunzip ${BACKUP_FILE}.gz${NC}"
    echo -e "  ${YELLOW}mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p $DB_NAME < $BACKUP_FILE${NC}"

else
    echo -e "\n${RED}❌ Backup failed!${NC}"
    echo -e "${RED}Please check your database connection and try again.${NC}"
    exit 1
fi
