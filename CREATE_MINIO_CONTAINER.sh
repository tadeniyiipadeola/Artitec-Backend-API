#!/bin/bash
# Command to create MinIO container on your Synology NAS
# Run this on your NAS after SSH'ing in

sudo docker run -d \
  --name minio \
  --restart unless-stopped \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=artitec-admin" \
  -e "MINIO_ROOT_PASSWORD=ArtitecMinIO2024!SecurePassword" \
  -v /volume1/docker/minio/data:/data \
  minio/minio server /data --console-address ":9001"
