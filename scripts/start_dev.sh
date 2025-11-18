#!/bin/bash
# Quick start script for development server

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_DIR/.venv"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Artitec Backend - Development Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

echo -e "${GREEN}✓${NC} Virtual environment activated"
echo -e "${GREEN}✓${NC} Starting development server..."
echo ""
echo "API will be available at:"
echo "  • http://127.0.0.1:8000"
echo "  • http://127.0.0.1:8000/docs (Swagger UI)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Start uvicorn
python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
