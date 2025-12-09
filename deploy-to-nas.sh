#!/bin/bash

# Artitec Backend - Deploy to NAS Script
# This script automates deployment to your NAS (100.94.199.71)

set -e

NAS_IP="100.94.199.71"
NAS_PATH="/volume1/docker/artitec-backend"
LOCAL_PATH="/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"

echo "🚀 Deploying Artitec Backend to NAS..."

# 1. Sync files to NAS
echo "📦 Syncing files to NAS..."
rsync -avz --exclude='.venv' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  "$LOCAL_PATH/" "$NAS_IP:$NAS_PATH/"

# 2. SSH into NAS and deploy
echo "🐳 Building and starting Docker container..."
ssh "$NAS_IP" << 'ENDSSH'
cd /volume1/docker/artitec-backend

# Stop existing container
echo "Stopping existing container..."
docker stop artitec-api 2>/dev/null || true
docker rm artitec-api 2>/dev/null || true

# Build new image
echo "Building Docker image..."
docker build -t artitec-backend:latest .

# Run new container
echo "Starting new container..."
docker run -d \
  --name artitec-api \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  -v $(pwd)/uploads:/app/uploads \
  artitec-backend:latest

# Show logs
echo "Container started! Showing logs..."
docker logs --tail 50 artitec-api

# Show status
echo ""
echo "✅ Deployment complete!"
docker ps | grep artitec
ENDSSH

echo ""
echo "✅ Deployment successful!"
echo "API is running at: http://100.94.199.71:8000"
echo "API Docs: http://100.94.199.71:8000/docs"
echo ""
echo "To view logs: ssh 100.94.199.71 'docker logs -f artitec-api'"
