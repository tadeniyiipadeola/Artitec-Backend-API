#!/bin/bash
# MinIO Installation Script for Synology NAS
# Simple version that avoids heredoc issues

echo "=========================================="
echo "MinIO Installation for Synology NAS"
echo "=========================================="
echo ""

# Step 1: Download and install MinIO
echo "Step 1: Installing MinIO..."
cd /tmp
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/
echo "✓ MinIO installed"
echo ""

# Step 2: Create data directory
echo "Step 2: Creating data directory..."
sudo mkdir -p /volume1/minio-data
sudo chown -R Developer /volume1/minio-data
echo "✓ Data directory created"
echo ""

# Step 3: Create config directory
echo "Step 3: Creating configuration..."
sudo mkdir -p /etc/minio

# Create config file using echo
echo "MINIO_ROOT_USER=artitec-admin" | sudo tee /etc/minio/minio.env > /dev/null
echo "MINIO_ROOT_PASSWORD=ArtitecMinIO2024!SecurePassword" | sudo tee -a /etc/minio/minio.env > /dev/null
echo "MINIO_VOLUMES=/volume1/minio-data" | sudo tee -a /etc/minio/minio.env > /dev/null
echo "MINIO_OPTS=--console-address :9001" | sudo tee -a /etc/minio/minio.env > /dev/null

echo "✓ Configuration created"
echo ""

# Step 4: Create startup script
echo "Step 4: Creating startup script..."
sudo mkdir -p /usr/local/etc/rc.d

echo "#!/bin/sh" | sudo tee /usr/local/etc/rc.d/minio.sh > /dev/null
echo "export MINIO_ROOT_USER=artitec-admin" | sudo tee -a /usr/local/etc/rc.d/minio.sh > /dev/null
echo "export MINIO_ROOT_PASSWORD=ArtitecMinIO2024!SecurePassword" | sudo tee -a /usr/local/etc/rc.d/minio.sh > /dev/null
echo "/usr/local/bin/minio server --console-address :9001 /volume1/minio-data > /var/log/minio.log 2>&1 &" | sudo tee -a /usr/local/etc/rc.d/minio.sh > /dev/null

sudo chmod +x /usr/local/etc/rc.d/minio.sh
echo "✓ Startup script created"
echo ""

# Step 5: Start MinIO
echo "Step 5: Starting MinIO..."
sudo sh /usr/local/etc/rc.d/minio.sh
sleep 3

# Check if running
if ps aux | grep -v grep | grep minio > /dev/null; then
    echo "✓ MinIO is running!"
else
    echo "⚠ MinIO may not be running. Check logs: tail /var/log/minio.log"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "MinIO Console: http://100.94.199.71:9001"
echo "MinIO API: http://100.94.199.71:9000"
echo ""
echo "Login Credentials:"
echo "  Username: artitec-admin"
echo "  Password: ArtitecMinIO2024!SecurePassword"
echo ""
echo "Next Steps:"
echo "1. Open http://100.94.199.71:9001 in your browser"
echo "2. Login with the credentials above"
echo "3. Create a bucket named 'artitec-media'"
echo "4. Generate access keys for your application"
echo ""
