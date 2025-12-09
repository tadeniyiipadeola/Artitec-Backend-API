# Start MinIO on NAS (100.94.199.71)

## Quick Start Commands

### 1. SSH into your NAS
```bash
ssh Admin@100.94.199.71
# Password: Password1
```

### 2. Check if MinIO container exists
```bash
sudo docker ps -a | grep minio
# You may need to enter your password again
```

### 3a. If MinIO exists but is stopped - Start it:
```bash
sudo docker start minio
# or use the container ID/name from step 2
sudo docker start <container-id>
```

### 3b. If MinIO doesn't exist - Create and start it:
```bash
sudo docker run -d \
  --name minio \
  --restart unless-stopped \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=artitec-admin" \
  -e "MINIO_ROOT_PASSWORD=ArtitecMinIO2024!SecurePassword" \
  -v /volume1/docker/minio/data:/data \
  minio/minio server /data --console-address ":9001"
```

**Note:** Adjust the volume path (`/volume1/docker/minio/data`) based on your NAS setup:
- Synology: `/volume1/docker/minio/data`
- QNAP: `/share/Container/minio/data`
- TrueNAS: `/mnt/tank/minio/data`

### 4. Verify MinIO is running
```bash
sudo docker ps | grep minio
curl http://localhost:9000
```

You should see MinIO responding.

### 5. Access MinIO Console (from your Mac)
Open in browser: http://100.94.199.71:9001

Login with:
- **Username:** artitec-admin
- **Password:** ArtitecMinIO2024!SecurePassword

### 6. Create the bucket (if it doesn't exist)
1. In MinIO Console, click "Buckets" → "Create Bucket"
2. Name: `artitec-media`
3. Click "Create"
4. Click on the bucket → "Access" tab
5. Set Access Policy to: **Public** or **Custom** with read access

### 7. Test from your Mac
```bash
curl http://100.94.199.71:9000
```

You should get a response from MinIO.

## Alternative: Use Docker Compose on NAS

If you prefer docker-compose, create this file on your NAS:

**minio-compose.yml:**
```yaml
version: '3.9'

services:
  minio:
    image: minio/minio:latest
    container_name: artitec-minio
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: artitec-admin
      MINIO_ROOT_PASSWORD: ArtitecMinIO2024!SecurePassword
    volumes:
      - /volume1/docker/minio/data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
```

Then run:
```bash
docker-compose -f minio-compose.yml up -d
```

---

## Once MinIO is running:

1. The backend will automatically connect using the credentials in `.env`
2. Media scraping will work through the iOS app
3. Images will be stored at: http://100.94.199.71:9000/artitec-media/[filename]

## Troubleshooting

**If port 9000 is already in use:**
```bash
# Check what's using port 9000
docker ps | grep 9000
# or
netstat -an | grep 9000
```

**Check MinIO logs:**
```bash
docker logs minio
# or
docker logs -f minio  # follow logs
```
