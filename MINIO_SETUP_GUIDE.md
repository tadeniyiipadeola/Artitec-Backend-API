# MinIO Setup Guide for Artitec Media Storage

This guide will help you set up MinIO on your NAS (100.94.199.71) for organized media storage.

## 📋 Overview

- **NAS IP**: 100.94.199.71
- **SSH User**: Developer
- **MinIO Console**: http://100.94.199.71:9001
- **MinIO API**: http://100.94.199.71:9000

## 🚀 Step 1: Install MinIO on NAS

### Option A: Using the Setup Script

1. SSH into your NAS:
```bash
ssh Developer@100.94.199.71
# Password: Password1
```

2. Copy and run the setup script:
```bash
# Download the setup script from your Mac
scp setup_minio_nas.sh Developer@100.94.199.71:~/

# Run the script
chmod +x ~/setup_minio_nas.sh
./setup_minio_nas.sh
```

### Option B: Manual Installation

1. SSH into your NAS:
```bash
ssh Developer@100.94.199.71
```

2. Download and install MinIO:
```bash
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/
```

3. Create data directory:
```bash
sudo mkdir -p /mnt/minio-data
sudo chown -R Developer:Developer /mnt/minio-data
```

4. Create MinIO service:
```bash
sudo mkdir -p /etc/minio
sudo tee /etc/minio/minio.env > /dev/null <<EOF
MINIO_ROOT_USER=artitec-admin
MINIO_ROOT_PASSWORD=ArtitecMinIO2024!SecurePassword
MINIO_VOLUMES=/mnt/minio-data
MINIO_OPTS="--console-address :9001"
EOF
```

5. Create systemd service:
```bash
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

[Install]
WantedBy=multi-user.target
EOF
```

6. Start MinIO:
```bash
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio
sudo systemctl status minio
```

## 🎯 Step 2: Configure MinIO

1. Access MinIO Console: http://100.94.199.71:9001

2. Login credentials:
   - **Username**: `artitec-admin`
   - **Password**: `ArtitecMinIO2024!SecurePassword`

3. Create bucket named `artitec-media`:
   - Click **"Buckets"** in left sidebar
   - Click **"Create Bucket"**
   - Bucket Name: `artitec-media`
   - Click **"Create Bucket"**

4. Set bucket to public access (for media serving):
   - Select `artitec-media` bucket
   - Click **"Manage"** → **"Access Policy"**
   - Select **"Public"**
   - Click **"Set"**

5. Create Access Keys for application:
   - Click **"Access Keys"** in left sidebar
   - Click **"Create Access Key"**
   - **Access Key**: (auto-generated, copy this)
   - **Secret Key**: (auto-generated, copy this)
   - Click **"Create"**
   - **Save these credentials!** You'll need them for the backend.

## 📁 Storage Structure

Media will be organized as:
```
artitec-media/
├── CMY-1763002158-W1Y12N/          # Community Profile ID
│   ├── gallery/                      # Gallery images
│   │   ├── image1.jpg
│   │   ├── image1_thumbnail.jpg
│   │   └── image1_medium.jpg
│   ├── profile/                      # Profile/Avatar images
│   │   └── avatar.jpg
│   ├── cover/                        # Cover photos
│   │   └── cover.jpg
│   └── video/                        # Video intros
│       └── intro.mp4
├── BLD-1699564234-X3P8Q1/          # Builder Profile ID
│   ├── gallery/
│   ├── profile/
│   └── video/
└── USR-1763002155-GRZVLL/          # User Profile ID
    ├── profile/
    └── gallery/
```

## ⚙️ Step 3: Configure Backend

Update `.env` file in your backend project:

```env
# Storage Configuration
STORAGE_TYPE=s3  # Changed from "local" to "s3"

# MinIO Configuration
S3_BUCKET_NAME=artitec-media
S3_ENDPOINT_URL=http://100.94.199.71:9000
AWS_ACCESS_KEY_ID=<your-access-key-from-step-2>
AWS_SECRET_ACCESS_KEY=<your-secret-key-from-step-2>
AWS_REGION=us-east-1

# Public Base URL for media access
S3_PUBLIC_BASE_URL=http://100.94.199.71:9000
```

## 🧪 Step 4: Test the Setup

1. Restart your backend server to pick up the new configuration

2. Test media upload via the scraper or upload endpoint

3. Check MinIO Console → `artitec-media` bucket to see organized folders

4. Verify images are accessible via URLs like:
   ```
   http://100.94.199.71:9000/artitec-media/CMY-123/gallery/image1.jpg
   ```

## 🔒 Security Recommendations

1. **Change default credentials** in `/etc/minio/minio.env`

2. **Use HTTPS** in production:
   - Set up reverse proxy (nginx/traefik)
   - Use SSL certificates

3. **Firewall rules**:
   ```bash
   sudo ufw allow 9000/tcp  # MinIO API
   sudo ufw allow 9001/tcp  # MinIO Console
   ```

4. **Backup configuration**:
   ```bash
   # Backup MinIO data periodically
   sudo tar -czf minio-backup-$(date +%Y%m%d).tar.gz /mnt/minio-data
   ```

## 📊 Monitoring

Check MinIO status:
```bash
sudo systemctl status minio
sudo journalctl -u minio -f  # View logs
```

Check disk usage:
```bash
du -sh /mnt/minio-data
```

## 🐛 Troubleshooting

### MinIO won't start
```bash
# Check logs
sudo journalctl -u minio -n 50

# Check permissions
ls -la /mnt/minio-data

# Restart service
sudo systemctl restart minio
```

### Can't access console
```bash
# Check if port is open
sudo netstat -tlnp | grep 9001

# Check firewall
sudo ufw status
```

### Upload fails
- Verify bucket exists and is set to public
- Check access keys are correct in `.env`
- Verify network connectivity from backend to NAS

## 📚 Additional Resources

- MinIO Documentation: https://docs.min.io
- MinIO Client (mc): https://docs.min.io/docs/minio-client-quickstart-guide.html

## ✅ Quick Reference

| Service | URL | Credentials |
|---------|-----|-------------|
| MinIO Console | http://100.94.199.71:9001 | artitec-admin / ArtitecMinIO2024!SecurePassword |
| MinIO API | http://100.94.199.71:9000 | Access Key / Secret Key |
| Bucket | artitec-media | Public |

