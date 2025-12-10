# Quick NAS Deployment - Manual Steps

Since automated deployment has some permission issues, here's the simplest way to deploy manually.

## Step 1: Package the Code (Already Done!)

The code is already packaged at `/tmp/artitec-backend.tar.gz`

## Step 2: Upload via Synology File Station

### Option A: Web Interface (Easiest)

1. Open your NAS web interface: http://100.94.199.71:5000
2. Log in with username: `Admin`, password: `Password1`
3. Open **File Station**
4. Navigate to `/docker/` (create this folder if it doesn't exist)
5. Create a new folder called `artitec-backend`
6. Upload the file `/tmp/artitec-backend.tar.gz` from your Mac to `/docker/artitec-backend/`

### Option B: SSH + wget (If you can access from Mac)

```bash
# On your Mac, start a simple HTTP server
cd /tmp
python3 -m http.server 8888

# Then SSH into NAS and download
ssh Admin@100.94.199.71
cd /volume1/docker/artitec-backend
wget http://192.168.4.73:8888/artitec-backend.tar.gz
```

## Step 3: SSH into NAS

```bash
ssh Admin@100.94.199.71
# Password: Password1
```

## Step 4: Extract and Deploy

Copy and paste these commands one at a time in your NAS SSH session:

```bash
# Navigate to directory
cd /volume1/docker
mkdir -p artitec-backend
cd artitec-backend

# If you uploaded via File Station, copy from there:
cp /volume1/[YOUR_SHARED_FOLDER]/artitec-backend.tar.gz .

# Extract
tar -xzf artitec-backend.tar.gz

# Stop any existing container
docker stop artitec-api 2>/dev/null || true
docker rm artitec-api 2>/dev/null || true

# Build Docker image (this will take 2-5 minutes)
docker build -t artitec-backend:latest .

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

## Step 5: Test the API

From your Mac or iPhone browser:

- **API Health**: http://100.94.199.71:8000/health
- **API Docs**: http://100.94.199.71:8000/docs

## Troubleshooting

### Docker command not found?

Your NAS might not have Docker installed. Check Synology Package Center and install "Docker".

### Permission denied?

Try adding `sudo` before docker commands:
```bash
sudo docker build -t artitec-backend:latest .
sudo docker run -d --name artitec-api ...
```

### Port 8000 already in use?

Check what's using it:
```bash
sudo netstat -tulpn | grep 8000
```

Or use a different port:
```bash
docker run -d --name artitec-api -p 8001:8000 ...
```

### Can't access from iPhone?

1. Make sure your NAS firewall allows port 8000
2. Try accessing from Mac first: http://100.94.199.71:8000/docs
3. Check if iPhone is on same network

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

## Future Updates

To update the backend:

1. Package code: `cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development" && tar -czf /tmp/artitec-backend.tar.gz --exclude='.venv' --exclude='.git' --exclude='__pycache__' .`
2. Upload to NAS (via File Station or wget)
3. SSH into NAS and run:
```bash
cd /volume1/docker/artitec-backend
tar -xzf artitec-backend.tar.gz
docker stop artitec-api && docker rm artitec-api
docker build -t artitec-backend:latest .
docker run -d --name artitec-api --network host --env-file .env --restart unless-stopped -v $(pwd)/uploads:/app/uploads artitec-backend:latest
```

That's it! Your backend is now running on your NAS.
