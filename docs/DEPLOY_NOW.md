# Deploy to NAS - Step by Step

Follow these steps to deploy your backend to the NAS.

## Option 1: Manual Deployment (Easiest)

### Step 1: Create Directory on NAS

SSH into your NAS and create the directory:

```bash
ssh YOUR_USERNAME@100.94.199.71
mkdir -p /volume1/docker/artitec-backend
exit
```

### Step 2: Copy Files to NAS

From your Mac terminal:

```bash
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"

# If using password authentication:
scp -r . YOUR_USERNAME@100.94.199.71:/volume1/docker/artitec-backend/

# Or use rsync (better, skips unnecessary files):
rsync -avz --exclude='.venv' --exclude='.git' --exclude='__pycache__' \
  . YOUR_USERNAME@100.94.199.71:/volume1/docker/artitec-backend/
```

### Step 3: Deploy on NAS

SSH into your NAS:

```bash
ssh YOUR_USERNAME@100.94.199.71
cd /volume1/docker/artitec-backend
```

Then run these commands on the NAS:

```bash
# Build the Docker image
docker build -t artitec-backend:latest .

# Stop any existing container
docker stop artitec-api 2>/dev/null || true
docker rm artitec-api 2>/dev/null || true

# Run the container
docker run -d \
  --name artitec-api \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  -v $(pwd)/uploads:/app/uploads \
  artitec-backend:latest

# Check if it's running
docker ps | grep artitec

# View logs
docker logs -f artitec-api
```

### Step 4: Test the API

From any browser or terminal:

```bash
# Health check
curl http://100.94.199.71:8000/health

# Open API docs in browser
open http://100.94.199.71:8000/docs
```

---

## Option 2: Use Existing SSH Session

If you already have an active SSH session to your NAS, you can deploy directly:

```bash
# Copy files using your existing credentials
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"

# Package the code
tar -czf /tmp/artitec-backend.tar.gz \
  --exclude='.venv' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .

# Now on your NAS (in your existing SSH session):
# 1. Upload the tar file to NAS
# 2. Extract it
# 3. Run docker build and docker run commands from Step 3 above
```

---

## Option 3: Docker Compose (Recommended)

If your NAS has docker-compose:

```bash
# SSH into NAS
ssh YOUR_USERNAME@100.94.199.71
cd /volume1/docker/artitec-backend

# Create docker-compose file
cat > docker-compose.yml << 'EOF'
version: "3.9"

services:
  api:
    build: .
    container_name: artitec-api
    network_mode: host
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped
EOF

# Deploy
docker-compose up -d --build

# View logs
docker-compose logs -f
```

---

## After Deployment

Your API will be accessible at:

- **API Base**: http://100.94.199.71:8000
- **API Docs**: http://100.94.199.71:8000/docs
- **Health Check**: http://100.94.199.71:8000/health

### Update Your iOS App

Edit `NetworkConfig.swift`:

```swift
static var apiBaseURL: String {
    #if DEBUG
    if let ngrokURL = ProcessInfo.processInfo.environment["NGROK_URL"], !ngrokURL.isEmpty {
        return ngrokURL
    }
    return "http://127.0.0.1:8000"
    #else
    // Production - NAS IP
    return "http://100.94.199.71:8000"
    #endif
}
```

Then in Xcode:
- For iPhone testing on same WiFi: Use `http://192.168.4.73:8000` in NGROK_URL
- For production: Use `http://100.94.199.71:8000`

---

## Troubleshooting

### Docker Not Installed on NAS?

```bash
# Install Docker (if needed)
wget -qO- https://get.docker.com/ | sh
```

### Permission Denied?

```bash
# Add your user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### Port 8000 Already in Use?

```bash
# Find what's using it
sudo lsof -i :8000
# Or use a different port
docker run -p 8001:8000 ...
```

### Can't Access from iPhone?

Make sure:
1. Firewall allows port 8000
2. iPhone is on same network as NAS
3. Try NAS IP from iPhone browser: http://100.94.199.71:8000/docs

---

## What's the Username for Your NAS?

Common Synology NAS usernames:
- `admin`
- Your Synology account username
- Check your NAS settings

If you're not sure, you can find it by checking your existing SSH sessions or NAS admin panel.
