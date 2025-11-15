#!/bin/bash
# MinIO Setup Script for NAS (100.94.199.71)
# Run this script on your NAS after SSH'ing in

set -e

echo "🚀 MinIO Setup for Artitec Media Storage"
echo "========================================"

# Check if MinIO is already installed
if command -v minio &> /dev/null; then
    echo "✅ MinIO is already installed"
    minio --version
else
    echo "📥 Installing MinIO..."

    # Download MinIO for Linux
    wget https://dl.min.io/server/minio/release/linux-amd64/minio
    chmod +x minio
    sudo mv minio /usr/local/bin/

    echo "✅ MinIO installed successfully"
fi

# Create MinIO data directory
echo "📁 Creating MinIO data directory..."
sudo mkdir -p /mnt/minio-data
sudo chown -R Developer:Developer /mnt/minio-data

# Create MinIO configuration directory
sudo mkdir -p /etc/minio
sudo chown -R Developer:Developer /etc/minio

# Create MinIO environment file
echo "📝 Creating MinIO configuration..."
sudo tee /etc/minio/minio.env > /dev/null <<EOF
# MinIO Configuration for Artitec
MINIO_ROOT_USER=artitec-admin
MINIO_ROOT_PASSWORD=ArtitecMinIO2024!SecurePassword
MINIO_VOLUMES=/mnt/minio-data
MINIO_OPTS="--console-address :9001"
EOF

# Create systemd service for MinIO
echo "⚙️ Creating MinIO service..."
sudo tee /etc/systemd/system/minio.service > /dev/null <<EOF
[Unit]
Description=MinIO Object Storage
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target

[Service]
User=Developer
Group=Developer
EnvironmentFile=/etc/minio/minio.env
ExecStart=/usr/local/bin/minio server \$MINIO_OPTS \$MINIO_VOLUMES
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start MinIO service
echo "🎬 Starting MinIO service..."
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio

# Check status
sudo systemctl status minio --no-pager

echo ""
echo "✅ MinIO Setup Complete!"
echo ""
echo "📊 MinIO Console: http://100.94.199.71:9001"
echo "🔌 MinIO API: http://100.94.199.71:9000"
echo "👤 Username: artitec-admin"
echo "🔑 Password: ArtitecMinIO2024!SecurePassword"
echo ""
echo "🔧 Next Steps:"
echo "1. Access MinIO Console at http://100.94.199.71:9001"
echo "2. Create bucket: artitec-media"
echo "3. Create access keys for the application"
echo ""
