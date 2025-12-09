# Deploy from GitHub to NAS - Super Simple!

This is the EASIEST way to deploy. Just SSH into your NAS and run a few commands.

## One-Time Setup (Do this once)

SSH into your NAS and run these commands:

```bash
ssh Admin@100.94.199.71
# Password: Password1

# Install git if not installed
sudo apt-get update && sudo apt-get install -y git

# Clone the repository
cd /volume1/docker
git clone https://github.com/tadeniyiipadeola/Artitec-Backend-API.git artitec-backend
cd artitec-backend

# Copy your .env file (do this once)
# Create .env with your database and other configs
cat > .env << 'EOF'
DB_URL=mysql+pymysql://Dev:Password1!@localhost:3306/appdb
JWT_SECRET=4de1f630069408ec9498579694ca657ea3e4dc0e13139a76c552068986d43eb303ed1cfe29b94f090bfc0a5dc7547c9f7b49e83dab97a7158155dfddc40213a7
JWT_ALG=HS256
JWT_ISS=artitec.api
ACCESS_TTL_MIN=120
REFRESH_TTL_DAYS=30
SECRET_KEY=2f3b0a33c6d1a7e95580aaabf58dc24ce2c8179bcd26a4e4180b4f21a8e67c12
APP_ENV=production
LOG_LEVEL=INFO
ANTHROPIC_API_KEY=your-anthropic-api-key-here
STORAGE_TYPE=s3
UPLOAD_DIR=uploads
BASE_URL=http://100.94.199.71:8000
S3_BUCKET_NAME=artitec-media
S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=artitec-admin
AWS_SECRET_ACCESS_KEY=ArtitecMinIO2024!SecurePassword
AWS_REGION=us-east-1
S3_PUBLIC_BASE_URL=http://100.94.199.71:9000/artitec-media
S3_SECURE=false
ADMIN_NOTIFICATION_EMAILS=supportteam@artitecplatform.com, adeniyi.temi.ta@gmail.com
FRONTEND_URL=http://100.94.199.71:8000
EOF

# Build and run
docker build -t artitec-backend:latest .
docker run -d \
  --name artitec-api \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  -v $(pwd)/uploads:/app/uploads \
  artitec-backend:latest

# Check if it's running
docker ps | grep artitec
docker logs -f artitec-api
```

## Future Updates (Every time you push changes)

When you push new code to GitHub, just run this on your NAS:

```bash
ssh Admin@100.94.199.71

cd /volume1/docker/artitec-backend

# Pull latest code
git pull

# Rebuild and restart
docker stop artitec-api
docker rm artitec-api
docker build -t artitec-backend:latest .
docker run -d \
  --name artitec-api \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  -v $(pwd)/uploads:/app/uploads \
  artitec-backend:latest

# Check logs
docker logs --tail 50 -f artitec-api
```

## Or Create a Simple Update Script

Create this script on your NAS to make updates even easier:

```bash
ssh Admin@100.94.199.71

cat > /volume1/docker/artitec-backend/update.sh << 'SCRIPT'
#!/bin/bash
cd /volume1/docker/artitec-backend
git pull
docker stop artitec-api
docker rm artitec-api
docker build -t artitec-backend:latest .
docker run -d --name artitec-api --network host --env-file .env --restart unless-stopped -v $(pwd)/uploads:/app/uploads artitec-backend:latest
docker ps | grep artitec
docker logs --tail 20 artitec-api
SCRIPT

chmod +x /volume1/docker/artitec-backend/update.sh
```

Then every time you push changes, just run:
```bash
ssh Admin@100.94.199.71 "/volume1/docker/artitec-backend/update.sh"
```

## Why This Is Better

1. ✅ **No file transfers** - Code comes directly from GitHub
2. ✅ **Version controlled** - Can rollback if needed
3. ✅ **Simple updates** - Just `git pull` and rebuild
4. ✅ **Works from anywhere** - GitHub is always accessible
5. ✅ **Clean and organized** - No manual file management

## Access Your API

Once deployed:
- **API**: http://100.94.199.71:8000
- **API Docs**: http://100.94.199.71:8000/docs
- **Health Check**: http://100.94.199.71:8000/health

## Troubleshooting

### Git not installed?
```bash
sudo apt-get update && sudo apt-get install -y git
```

### Can't clone (authentication)?
The repo is public, so no authentication needed. If you have issues:
```bash
git clone https://github.com/tadeniyiipadeola/Artitec-Backend-API.git
```

### Docker not found?
Install Docker from Synology Package Center.

### Port 8000 in use?
```bash
# Check what's using it
sudo netstat -tulpn | grep 8000

# Stop it
sudo kill $(sudo lsof -t -i:8000)
```

## Update iOS App

Once deployed, update `NetworkConfig.swift`:

```swift
static var apiBaseURL: String {
    #if DEBUG
    if let ngrokURL = ProcessInfo.processInfo.environment["NGROK_URL"], !ngrokURL.isEmpty {
        return ngrokURL
    }
    return "http://127.0.0.1:8000"
    #else
    // Production - NAS
    return "http://100.94.199.71:8000"
    #endif
}
```

That's it! Super simple deployment via GitHub.
