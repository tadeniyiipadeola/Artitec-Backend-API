#!/bin/bash
# Quick deployment script to update Artitec Backend on NAS from GitHub

set -e

NAS_IP="100.94.199.71"
NAS_USER="Admin"
NAS_PASSWORD="Password1"
DEPLOY_DIR="/volume1/docker/Artitec-Backend-API"

echo "🚀 Starting Artitec Backend deployment update..."
echo ""

# SSH into NAS and run deployment commands
sshpass -p "$NAS_PASSWORD" ssh -o StrictHostKeyChecking=no "$NAS_USER@$NAS_IP" << 'ENDSSH'

set -e

echo "📂 Navigating to deployment directory..."
cd /volume1/docker/Artitec-Backend-API

echo "📥 Pulling latest changes from GitHub..."
sudo git pull origin main

echo "🛑 Stopping current container..."
sudo docker stop artitec-api || true
sudo docker rm artitec-api || true

echo "🐳 Building new Docker image..."
sudo docker build -t artitec-backend:latest .

echo "🚀 Starting new container..."
sudo docker run -d \
  --name artitec-api \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  -v $(pwd)/uploads:/app/uploads \
  artitec-backend:latest

echo "⏳ Waiting for container to start..."
sleep 5

echo ""
echo "✅ Container status:"
sudo docker ps | grep artitec

echo ""
echo "📋 Recent logs:"
sudo docker logs --tail 20 artitec-api

echo ""
echo "✅ Deployment complete!"
echo "API running at: http://100.94.199.71:8000"
echo "API Docs: http://100.94.199.71:8000/docs"

ENDSSH

echo ""
echo "✅ Update deployment completed successfully!"
