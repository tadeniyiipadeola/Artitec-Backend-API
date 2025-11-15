#!/bin/sh
# Complete MinIO installation script for Synology NAS
# Run this on your NAS with: sudo sh complete_minio_install.sh

echo "Starting MinIO installation..."

# Remove old startup script if exists
rm -f /usr/local/etc/rc.d/minio.sh

# Create startup script
cat > /tmp/minio_start.sh << 'ENDOFFILE'
#!/bin/sh
export MINIO_ROOT_USER=artitec-admin
export MINIO_ROOT_PASSWORD=ArtitecMinIO2024!SecurePassword
/usr/local/bin/minio server --console-address :9001 /volume1/minio-data > /var/log/minio.log 2>&1 &
ENDOFFILE

# Move to proper location
mv /tmp/minio_start.sh /usr/local/etc/rc.d/minio.sh
chmod +x /usr/local/etc/rc.d/minio.sh

echo "Starting MinIO..."
sh /usr/local/etc/rc.d/minio.sh

echo "Waiting for MinIO to start..."
sleep 5

echo "Checking if MinIO is running..."
ps aux | grep minio | grep -v grep

echo ""
echo "Installation complete!"
echo "MinIO Console: http://100.94.199.71:9001"
echo "Username: artitec-admin"
echo "Password: ArtitecMinIO2024!SecurePassword"
