# Quick Start: MinIO on Your Synology NAS

## Step-by-Step Commands

### 1. Open Terminal and SSH to your NAS:
```bash
ssh Admin@100.94.199.71
```
**Password:** `Password1`

---

### 2. Once logged in, check if MinIO exists:
```bash
sudo docker ps -a | grep minio
```
**Password:** `Password1` (if prompted)

---

### 3. Start MinIO:

**If MinIO container exists:**
```bash
sudo docker start minio
```

**If MinIO doesn't exist (create it):**
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

---

### 4. Verify it's running:
```bash
sudo docker ps | grep minio
```

You should see output showing the minio container is running with ports 9000 and 9001.

---

### 5. Exit the NAS:
```bash
exit
```

---

### 6. Test from your Mac:
```bash
curl http://100.94.199.71:9000
```

You should get an XML response from MinIO.

---

### 7. Access MinIO Web Console (optional):
Open in browser: **http://100.94.199.71:9001**

Login:
- **Username:** artitec-admin
- **Password:** ArtitecMinIO2024!SecurePassword

---

### 8. Create the bucket (if needed):
1. In MinIO Console, click "Buckets" → "Create Bucket"
2. Name: `artitec-media`
3. Click "Create"
4. Click on the bucket → "Access" tab
5. Set Access Policy to: **Public** or **Custom** with read access

---

## Done!

Your backend is already configured to use this MinIO server.
Test media scraping through your iOS app's MediaScraperView.
