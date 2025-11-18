#!/bin/bash
# Setup script for scheduling automatic orphan cleanup
# This script helps configure a cron job to run orphan cleanup daily

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the absolute path to the project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_DIR/.venv"
LOG_DIR="$PROJECT_DIR/logs"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Orphan Cleanup Cron Job Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    echo "Please create a virtual environment first"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"
echo -e "${GREEN}✓${NC} Logs directory: $LOG_DIR"

# Create the cron job command
CRON_CMD="0 2 * * * cd $PROJECT_DIR && source $VENV_PATH/bin/activate && python -m src.cleanup_orphans >> $LOG_DIR/orphan_cleanup.log 2>&1"

echo ""
echo -e "${YELLOW}Proposed cron job:${NC}"
echo "  $CRON_CMD"
echo ""
echo "This will run daily at 2:00 AM and log to: $LOG_DIR/orphan_cleanup.log"
echo ""

# Ask user if they want to install the cron job
read -p "Do you want to install this cron job? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "cleanup_orphans"; then
        echo -e "${YELLOW}⚠${NC}  Existing orphan cleanup cron job found"
        read -p "Do you want to replace it? (y/n) " -n 1 -r
        echo ""

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Remove old cron job
            crontab -l 2>/dev/null | grep -v "cleanup_orphans" | crontab -
            echo -e "${GREEN}✓${NC} Removed old cron job"
        else
            echo -e "${YELLOW}Keeping existing cron job${NC}"
            exit 0
        fi
    fi

    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo -e "${GREEN}✓${NC} Cron job installed successfully!"
    echo ""
    echo "To view your cron jobs: crontab -l"
    echo "To remove this cron job: crontab -e (then delete the line)"
    echo ""
    echo -e "${GREEN}Manual test commands:${NC}"
    echo "  # Dry run (preview only):"
    echo "  cd $PROJECT_DIR && source $VENV_PATH/bin/activate && python -m src.cleanup_orphans --dry-run"
    echo ""
    echo "  # Actual cleanup:"
    echo "  cd $PROJECT_DIR && source $VENV_PATH/bin/activate && python -m src.cleanup_orphans"
else
    echo ""
    echo -e "${YELLOW}Cron job not installed${NC}"
    echo ""
    echo "To manually install later, run:"
    echo "  (crontab -l 2>/dev/null; echo \"$CRON_CMD\") | crontab -"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete${NC}"
echo -e "${GREEN}========================================${NC}"
