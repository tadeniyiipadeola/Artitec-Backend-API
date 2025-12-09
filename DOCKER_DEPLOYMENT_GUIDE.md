# Docker Deployment Guide

This guide covers deploying the Artitec backend using Docker.

## Table of Contents
1. [Local Development with Docker](#local-development)
2. [Production Deployment](#production-deployment)
3. [CI/CD with GitHub Actions](#cicd-setup)
4. [Deployment Platforms](#deployment-platforms)

---

## Local Development

### Test with Docker Locally

```bash
# Build and run with docker-compose
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
docker-compose -f docker-compose.local.yaml up --build

# This will start:
# - Backend API on port 8000
# - MySQL database on port 3307
# - MinIO (S3) on ports 9000 (API) and 9001 (Console)
```

### Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001
  - Username: `artitec-admin`
  - Password: `ArtitecMinIO2024!SecurePassword`

### Stop Services

```bash
docker-compose -f docker-compose.local.yaml down

# To remove volumes as well:
docker-compose -f docker-compose.local.yaml down -v
```

---

## Production Deployment

### Prerequisites

1. A server (VPS) with Docker installed
2. Domain name (optional but recommended)
3. SSL certificate (Let's Encrypt)

### Setup on Production Server

#### 1. Prepare Server

```bash
# SSH into your server
ssh user@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Clone Repository

```bash
# Create directory
sudo mkdir -p /opt/artitec-backend
cd /opt/artitec-backend

# Clone your repo (or upload files)
git clone https://github.com/TADENIYIIPADEOLA/artitec-backend.git .
```

#### 3. Configure Environment

```bash
# Copy production environment template
cp .env.prod.example .env.prod

# Edit production environment
nano .env.prod
```

Update these critical values:
- `DB_URL` - Your production database URL
- `JWT_SECRET` - Generate a new secret key
- `SECRET_KEY` - Generate a new secret key
- `ANTHROPIC_API_KEY` - Your API key
- `S3_ENDPOINT_URL` - Your MinIO/S3 endpoint
- `FRONTEND_URL` - Your production frontend URL

#### 4. Start Production Services

```bash
# Pull latest image
docker-compose -f docker-compose.prod.yaml pull

# Start services
docker-compose -f docker-compose.prod.yaml up -d

# Check logs
docker-compose -f docker-compose.prod.yaml logs -f api
```

### Run Database Migrations

```bash
# Run migrations inside the container
docker exec -it artitec-api-prod alembic upgrade head
```

---

## CI/CD Setup

### GitHub Actions Auto-Deployment

The repository includes a GitHub Actions workflow that automatically builds and deploys on push to main.

#### Setup GitHub Secrets

Go to your GitHub repository → Settings → Secrets → Actions, and add:

1. **PROD_SERVER_HOST**: Your production server IP or domain
2. **PROD_SERVER_USER**: SSH username (e.g., `root` or `ubuntu`)
3. **PROD_SERVER_SSH_KEY**: Your SSH private key

#### How It Works

1. Push code to `main` branch
2. GitHub Actions builds Docker image
3. Image is pushed to GitHub Container Registry
4. Watchtower on production server automatically pulls and restarts

#### Manual Deployment

```bash
# Trigger deployment manually from GitHub UI:
# Actions → Build and Deploy → Run workflow
```

---

## Deployment Platforms

### Option 1: DigitalOcean (Recommended)

**Cost**: $6/month (basic droplet)

1. Create a Droplet (Ubuntu 22.04)
2. Follow "Setup on Production Server" steps above
3. Configure firewall:
   ```bash
   ufw allow 22   # SSH
   ufw allow 80   # HTTP
   ufw allow 443  # HTTPS
   ufw allow 8000 # API
   ufw enable
   ```

### Option 2: AWS EC2

**Cost**: ~$5-10/month (t2.micro or t3.micro)

1. Launch EC2 instance (Ubuntu 22.04)
2. Configure Security Group (ports 22, 80, 443, 8000)
3. Follow "Setup on Production Server" steps above

### Option 3: Railway.app

**Cost**: $5/month (Hobby plan)

1. Connect GitHub repository
2. Railway auto-detects Dockerfile
3. Add environment variables in Railway dashboard
4. Deploy automatically on git push

### Option 4: Render.com

**Cost**: Free tier available, $7/month for production

1. Connect GitHub repository
2. Select "Docker" as environment
3. Add environment variables
4. Deploy

### Option 5: Fly.io

**Cost**: Free tier available

1. Install flyctl CLI
2. Run `fly launch` in project directory
3. Configure fly.toml
4. Deploy with `fly deploy`

---

## SSL/HTTPS Setup

### Using Nginx + Let's Encrypt

```bash
# Install Nginx
sudo apt install nginx

# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d api.artitecplatform.com

# Configure Nginx
sudo nano /etc/nginx/sites-available/artitec
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name api.artitecplatform.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api.artitecplatform.com;

    ssl_certificate /etc/letsencrypt/live/api.artitecplatform.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.artitecplatform.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/artitec /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Updating iOS App for Production

Once deployed, update your iOS app's NetworkConfig.swift:

```swift
static var apiBaseURL: String {
    #if DEBUG
    if let ngrokURL = ProcessInfo.processInfo.environment["NGROK_URL"], !ngrokURL.isEmpty {
        return ngrokURL
    }
    return "http://127.0.0.1:8000"
    #else
    // Production URL
    return "https://api.artitecplatform.com"  // Your production domain
    #endif
}
```

---

## Monitoring

### View Logs

```bash
# API logs
docker logs -f artitec-api-prod

# All services
docker-compose -f docker-compose.prod.yaml logs -f
```

### Check Container Status

```bash
docker ps
docker-compose -f docker-compose.prod.yaml ps
```

### Restart Services

```bash
docker-compose -f docker-compose.prod.yaml restart api
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs artitec-api-prod

# Check if port is already in use
sudo lsof -i :8000
```

### Database Connection Issues

```bash
# Test database connection from container
docker exec -it artitec-api-prod python -c "from sqlalchemy import create_engine; engine = create_engine('YOUR_DB_URL'); print(engine.connect())"
```

### Permission Issues

```bash
# Fix upload directory permissions
sudo chown -R 1000:1000 /opt/artitec-backend/uploads
```

---

## Cost Summary

| Platform | Monthly Cost | Notes |
|----------|-------------|-------|
| DigitalOcean | $6 | Best value, easy setup |
| AWS EC2 | $5-10 | Free tier for 1 year |
| Railway | $5 | Auto-deployment, easy |
| Render | $7 | Free tier available |
| Fly.io | Free-$5 | Generous free tier |

**Recommendation**: Start with DigitalOcean $6/month droplet or Railway $5/month.
