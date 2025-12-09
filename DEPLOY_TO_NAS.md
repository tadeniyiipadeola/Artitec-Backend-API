# Deploy to Your NAS (100.94.199.71)

This guide will help you deploy the Artitec backend to your NAS using Docker.

## Why Use Your NAS?

✅ You already have it running 24/7
✅ MinIO is already running there
✅ MySQL database is there
✅ No additional hosting costs
✅ Full control over your infrastructure

## Prerequisites

- SSH access to your NAS (100.94.199.71)
- Docker installed on NAS
- Your NAS is accessible from the internet (or you'll use it on local network)

---

## Quick Deployment Steps

### 1. Copy Files to NAS

From your Mac, copy the backend code to your NAS:

```bash
# Create directory on NAS
ssh 100.94.199.71 "mkdir -p /volume1/docker/artitec-backend"

# Copy all files
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
rsync -avz --exclude='.venv' --exclude='.git' --exclude='__pycache__' \
  . 100.94.199.71:/volume1/docker/artitec-backend/
```

### 2. SSH into Your NAS

```bash
ssh 100.94.199.71
cd /volume1/docker/artitec-backend
```

### 3. Create Production Environment File

```bash
cp .env .env.prod

# Edit if needed (your database is already configured)
nano .env.prod
```

Make sure these are correct:
- `DB_URL=mysql+pymysql://Dev:Password1!@localhost:3306/appdb`
- `S3_ENDPOINT_URL=http://localhost:9000`

### 4. Build and Run

```bash
# Build the Docker image
docker build -t artitec-backend:latest .

# Run the container
docker run -d \
  --name artitec-api \
  --network host \
  --env-file .env.prod \
  --restart unless-stopped \
  -v $(pwd)/uploads:/app/uploads \
  artitec-backend:latest
```

Using `--network host` allows the container to access MySQL and MinIO on localhost.

### 5. Verify It's Running

```bash
# Check container status
docker ps | grep artitec

# Check logs
docker logs -f artitec-api

# Test the API
curl http://localhost:8000/health
curl http://100.94.199.71:8000/docs
```

---

## Alternative: Using Docker Compose on NAS

Create a simplified docker-compose file for NAS:

```bash
cat > docker-compose.nas.yaml << 'EOF'
version: "3.9"

services:
  api:
    build: .
    container_name: artitec-api
    network_mode: host
    env_file:
      - .env.prod
    volumes:
      - ./uploads:/app/uploads
      - ./alembic:/app/alembic
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 5
EOF
```

Then run:

```bash
docker-compose -f docker-compose.nas.yaml up -d --build
```

---

## Accessing Your API

### From Local Network

Your backend will be accessible at:
- **API**: http://192.168.4.73:8000 (if NAS is on same network)
- **API Docs**: http://192.168.4.73:8000/docs

### From Internet (Port Forwarding)

If you want to access from anywhere:

1. Configure port forwarding on your router:
   - External Port: 8000
   - Internal IP: 100.94.199.71
   - Internal Port: 8000

2. Get your public IP: https://whatismyipaddress.com

3. Access API at: `http://YOUR_PUBLIC_IP:8000`

### With Domain Name (Recommended)

1. Buy a domain (e.g., artitecapi.com) - $10-15/year
2. Point domain to your public IP
3. Set up Dynamic DNS if your IP changes
4. Access API at: `http://artitecapi.com:8000`

---

## SSL/HTTPS Setup (Optional but Recommended)

### Using Cloudflare Tunnel (Free & Easy)

This gives you HTTPS without port forwarding!

```bash
# Install cloudflared on NAS
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create artitec-api

# Configure tunnel
cat > config.yml << 'EOF'
tunnel: artitec-api
credentials-file: /root/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel --config config.yml run artitec-api
```

Now your API is accessible at `https://api.yourdomain.com` with automatic HTTPS!

---

## Update iOS App to Use NAS

Update `NetworkConfig.swift`:

```swift
static var apiBaseURL: String {
    #if DEBUG
    if let ngrokURL = ProcessInfo.processInfo.environment["NGROK_URL"], !ngrokURL.isEmpty {
        return ngrokURL
    }
    return "http://127.0.0.1:8000"
    #else
    // Production - your NAS
    return "http://YOUR_PUBLIC_IP:8000"  // or http://api.yourdomain.com
    #endif
}
```

---

## Automatic Updates

### Option 1: Manual Updates

```bash
# SSH into NAS
ssh 100.94.199.71
cd /volume1/docker/artitec-backend

# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.nas.yaml up -d --build
```

### Option 2: Watchtower Auto-Updates

Add watchtower to docker-compose.nas.yaml:

```yaml
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_POLL_INTERVAL=300
      - WATCHTOWER_CLEANUP=true
    restart: unless-stopped
```

---

## Monitoring

### View Logs

```bash
# Real-time logs
docker logs -f artitec-api

# Last 100 lines
docker logs --tail 100 artitec-api
```

### Check Container Status

```bash
docker ps
docker stats artitec-api
```

### Restart API

```bash
docker restart artitec-api
```

---

## Database Migrations

Run migrations on NAS:

```bash
# Execute inside container
docker exec -it artitec-api alembic upgrade head

# Or if using docker-compose
docker-compose -f docker-compose.nas.yaml exec api alembic upgrade head
```

---

## Backup Strategy

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/volume1/backups/artitec"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker exec mysql mysqldump -u Dev -pPassword1! appdb > $BACKUP_DIR/db_$DATE.sql

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz uploads/

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

---

## Troubleshooting

### Can't Connect to MySQL

The container needs to access MySQL on the host:

```bash
# Use host.docker.internal or host network mode
DB_URL=mysql+pymysql://Dev:Password1!@host.docker.internal:3306/appdb
```

Or use `--network host` when running docker.

### Port 8000 Already in Use

```bash
# Check what's using it
sudo lsof -i :8000

# Stop the process or use a different port
docker run -p 8001:8000 ...
```

### Permission Errors

```bash
# Fix upload directory
sudo chown -R 1000:1000 uploads/
sudo chmod -R 755 uploads/
```

---

## Cost Comparison

| Option | Cost | Notes |
|--------|------|-------|
| **Your NAS** | $0/month | Already running, already paid for |
| DigitalOcean | $6/month | Simple VPS |
| AWS EC2 | $5-10/month | More complex |
| Railway | $5/month | Easy but costs money |

**Recommendation**: Start with your NAS (free!), then move to cloud hosting if you need better uptime or global access.
