# Artitec Backend Deployment Pipeline

This document explains how to quickly deploy updates to your NAS after pushing changes to GitHub.

## Quick Deployment Options

### Option 1: Using the Expect Script (Recommended)

This is the easiest and most reliable method:

```bash
# From your Mac terminal
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
./quick-deploy.exp
```

**What it does:**
1. Connects to your NAS via SSH
2. Pulls the latest code from GitHub
3. Rebuilds the Docker image
4. Restarts the container with the new code
5. Shows you the logs to verify it's running

**Time:** ~3-5 minutes total

### Option 2: Manual Commands (Fast if you're already SSH'd in)

If you're already connected to the NAS via SSH:

```bash
cd /volume1/docker/Artitec-Backend-API
sudo git pull origin main
sudo docker stop artitec-api && sudo docker rm artitec-api
sudo docker build -t artitec-backend:latest .
sudo docker run -d --name artitec-api --network host --env-file .env --restart unless-stopped -v $(pwd)/uploads:/app/uploads artitec-backend:latest
sudo docker logs --tail 20 artitec-api
```

### Option 3: One-Liner from Mac (Requires sshpass)

```bash
./deploy-update.sh
```

First install sshpass if needed:
```bash
brew install hudochenkov/sshpass/sshpass
```

## Typical Development Workflow

### 1. Make Changes Locally

```bash
# Edit your code
vim src/routes/some_file.py

# Test locally
.venv/bin/uvicorn src.app:app --reload
```

### 2. Commit and Push to GitHub

```bash
git add .
git commit -m "Add new feature or fix bug"
git push origin main
```

### 3. Deploy to NAS

```bash
# Quick deployment
./quick-deploy.exp
```

### 4. Verify on iPhone

- Open your iPhone Artitec app
- Make sure you're on the same WiFi
- Test the new feature/fix

## Deployment Checklist

Before deploying:
- [ ] Code is committed and pushed to GitHub
- [ ] Local tests pass
- [ ] No sensitive data in code (API keys should be in .env)
- [ ] Database migrations run locally (if any)

After deploying:
- [ ] Container is running: `sudo docker ps | grep artitec`
- [ ] No errors in logs: `sudo docker logs --tail 50 artitec-api`
- [ ] API responds: http://100.94.199.71:8000/health
- [ ] Test from iPhone app

## Troubleshooting

### Container won't start

Check logs:
```bash
sudo docker logs artitec-api
```

### Port already in use

Stop old container:
```bash
sudo docker stop artitec-api
sudo docker rm artitec-api
```

### Git pull fails

Reset and pull:
```bash
cd /volume1/docker/Artitec-Backend-API
sudo git reset --hard origin/main
sudo git pull
```

### Need to update .env file

SSH into NAS and edit:
```bash
ssh Admin@100.94.199.71
cd /volume1/docker/Artitec-Backend-API
sudo nano .env
# Make changes, then Ctrl+X, Y, Enter
```

Then redeploy:
```bash
./quick-deploy.exp
```

## Database Migrations

If you have database schema changes:

```bash
# SSH into NAS
ssh Admin@100.94.199.71
cd /volume1/docker/Artitec-Backend-API

# Run migrations inside the container
sudo docker exec -it artitec-api alembic upgrade head
```

## Rollback to Previous Version

If something goes wrong:

```bash
# SSH into NAS
ssh Admin@100.94.199.71
cd /volume1/docker/Artitec-Backend-API

# Check git log
sudo git log --oneline -n 10

# Rollback to specific commit
sudo git reset --hard <commit-hash>

# Redeploy
sudo docker stop artitec-api && sudo docker rm artitec-api
sudo docker build -t artitec-backend:latest .
sudo docker run -d --name artitec-api --network host --env-file .env --restart unless-stopped -v $(pwd)/uploads:/app/uploads artitec-backend:latest
```

## Advanced: Auto-Deploy on Git Push (Optional)

You can set up a webhook or GitHub Action to automatically deploy when you push to main:

1. Create a GitHub Action (`.github/workflows/deploy.yml`)
2. Or use a simple webhook listener on your NAS

This is optional and can be set up later if needed.

## API Endpoints

After deployment, your API is available at:

- **Base URL**: http://100.94.199.71:8000
- **Docs**: http://100.94.199.71:8000/docs
- **Health**: http://100.94.199.71:8000/health
- **OpenAPI**: http://100.94.199.71:8000/openapi.json

## Monitoring

Check container status:
```bash
sudo docker ps | grep artitec
```

Follow live logs:
```bash
sudo docker logs -f artitec-api
```

Check container resource usage:
```bash
sudo docker stats artitec-api
```

## Support

If you encounter issues, check:
1. Container logs: `sudo docker logs artitec-api`
2. NAS disk space: `df -h`
3. Docker images: `sudo docker images`
4. Network connectivity: `ping 100.94.199.71`
