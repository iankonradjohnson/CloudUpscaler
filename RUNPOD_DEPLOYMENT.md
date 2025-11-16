# RunPod Serverless Deployment Guide

Complete guide to deploying CloudUpscaler handler to RunPod Serverless.

## Prerequisites

1. **RunPod Account** - Sign up at https://runpod.io
2. **Docker Hub Account** - For pushing Docker images
3. **Docker Image Built** - See main README

## Step 1: Push Docker Image to Registry

### Option A: Docker Hub (Recommended)

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler/docker

# Login to Docker Hub
docker login

# Tag image for Docker Hub
docker tag iankonradjohnson/realesrgan-runpod:latest \
  YOUR_DOCKERHUB_USERNAME/realesrgan-runpod:latest

# Push to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/realesrgan-runpod:latest
```

### Option B: RunPod Container Registry

```bash
# Login to RunPod registry
docker login registry.runpod.io

# Tag for RunPod
docker tag iankonradjohnson/realesrgan-runpod:latest \
  registry.runpod.io/YOUR_RUNPOD_USERNAME/realesrgan-runpod:latest

# Push to RunPod
docker push registry.runpod.io/YOUR_RUNPOD_USERNAME/realesrgan-runpod:latest
```

## Step 2: Create RunPod Serverless Endpoint

### Via Web UI

1. **Go to RunPod Console**
   - Navigate to https://www.runpod.io/console/serverless

2. **Click "New Endpoint"**

3. **Configure Endpoint:**
   - **Name:** `cloud-upscaler` or `realesrgan-upscaler`
   - **Docker Image:** `YOUR_DOCKERHUB_USERNAME/realesrgan-runpod:latest`
   - **GPU Type:** Select GPU (RTX 3090, RTX 4090, or A40 recommended)
   - **Container Disk:** 20 GB minimum
   - **Max Workers:** 3-5 (adjust based on budget)
   - **Min Workers:** 0 (serverless, scales to zero)
   - **Idle Timeout:** 5 seconds (for cost savings)

4. **Environment Variables:**
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs_credentials.json
   ```

5. **Click "Deploy"**

### Via RunPod CLI (Alternative)

```bash
# Install RunPod CLI
pip install runpod-cli

# Login
runpod login

# Create endpoint
runpod endpoint create \
  --name cloud-upscaler \
  --image YOUR_DOCKERHUB_USERNAME/realesrgan-runpod:latest \
  --gpu RTX3090 \
  --workers-min 0 \
  --workers-max 5 \
  --container-disk 20 \
  --idle-timeout 5
```

## Step 3: Get API Credentials

After deployment, you'll receive:

1. **Endpoint ID** - e.g., `abc123def456`
2. **API Key** - e.g., `XXXXXXXXXXXXXXXXXXXXXX`

Save these for your CloudUpscaler client configuration!

## Step 4: Configure Google Cloud Storage

### Create GCS Bucket

```bash
# Install gcloud CLI (if not already)
# https://cloud.google.com/sdk/docs/install

# Create bucket
gsutil mb gs://YOUR-BUCKET-NAME

# Set public access (for signed URLs)
gsutil iam ch allUsers:objectViewer gs://YOUR-BUCKET-NAME
```

### Create Service Account

```bash
# Create service account
gcloud iam service-accounts create cloud-upscaler \
    --display-name="CloudUpscaler Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:cloud-upscaler@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Create key
gcloud iam service-accounts keys create ~/gcs-credentials.json \
    --iam-account=cloud-upscaler@YOUR-PROJECT-ID.iam.gserviceaccount.com
```

## Step 5: Configure CloudUpscaler Client

### Set Environment Variables

```bash
# Add to your ~/.zshrc or ~/.bashrc
export RUNPOD_API_KEY="your_runpod_api_key"
export RUNPOD_ENDPOINT_ID="your_endpoint_id"
export GCS_BUCKET="your-bucket-name"
export GCS_PROJECT_ID="your-gcp-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcs-credentials.json"
```

Or create `.env` file:

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler
cp .env.example .env
# Edit .env with your credentials
```

## Step 6: Test the Deployment

### Test via CLI

```bash
cd /Users/iankonradjohnson/base/abacus/CloudUpscaler
source venv/bin/activate

# Test with cloud mode
cloud-upscaler test_images_input/ test_images_output/ --cloud

# Should see:
# ✓ SUCCESS: Processed 3 images
```

### Test via Python

```python
from cloud_upscaler import upscale_images
from cloud_upscaler.providers.gcs import GoogleCloudStorageProvider
from cloud_upscaler.providers.runpod import RunPodComputeProvider
from pathlib import Path
import os

# Initialize providers
storage = GoogleCloudStorageProvider(
    bucket_name=os.getenv("GCS_BUCKET"),
    project_id=os.getenv("GCS_PROJECT_ID")
)

compute = RunPodComputeProvider(
    api_key=os.getenv("RUNPOD_API_KEY"),
    endpoint_id=os.getenv("RUNPOD_ENDPOINT_ID"),
    output_bucket=os.getenv("GCS_BUCKET"),
    output_path="upscaled/output.zip"
)

# Run upscaling
result = upscale_images(
    input_dir=Path("test_images_input"),
    output_dir=Path("test_images_output"),
    storage_provider=storage,
    compute_provider=compute
)

print(result)
```

### Test via MCP Server

```bash
# In Claude Code, run:
/mcp

# Then ask Claude:
# "Please upscale images in ~/test_images_input to ~/test_images_output"
```

## Monitoring & Debugging

### Check RunPod Logs

```bash
# Via CLI
runpod endpoint logs ENDPOINT_ID

# Or via web UI:
# https://www.runpod.io/console/serverless/ENDPOINT_ID/logs
```

### Check Job Status

```bash
# Via Python
from cloud_upscaler.providers.runpod import RunPodComputeProvider

provider = RunPodComputeProvider(
    api_key=os.getenv("RUNPOD_API_KEY"),
    endpoint_id=os.getenv("RUNPOD_ENDPOINT_ID"),
    output_bucket=os.getenv("GCS_BUCKET"),
    output_path="upscaled/output.zip"
)

# Get status
status = provider.get_job_status("job_id")
print(f"Job status: {status}")
```

### Common Issues

**Issue:** "Handler not found"
**Solution:** Verify `handler.py` and all dependencies are in the Docker image

**Issue:** "Model weights not found"
**Solution:** Ensure Dockerfile downloads weights to `/weights/`

**Issue:** "GCS permission denied"
**Solution:** Check service account has `roles/storage.objectAdmin`

**Issue:** "RunPod timeout"
**Solution:** Increase `--timeout` parameter in CLI or adjust worker configuration

## Cost Optimization

### Minimize Costs

1. **Use Spot Instances** - 50-70% cheaper
   ```bash
   # In endpoint config, enable "Spot Instances"
   ```

2. **Set Idle Timeout Low** - Scale to zero when not in use
   ```bash
   # Set idle timeout to 5 seconds
   ```

3. **Use Smaller GPUs for Testing** - RTX 3060 for development
   ```bash
   # Switch to cheaper GPU during testing
   ```

4. **Batch Processing** - Process multiple images per job
   ```bash
   # Put more images in input directory
   ```

### Estimated Costs

- **RTX 3090:** ~$0.30/hour
- **RTX 4090:** ~$0.50/hour
- **A40:** ~$0.60/hour

For 100 images (~5 minutes): **$0.02-$0.05 per batch**

## Production Checklist

- [ ] Docker image pushed to registry
- [ ] RunPod endpoint created and deployed
- [ ] GCS bucket created with proper permissions
- [ ] Service account credentials generated
- [ ] Environment variables configured
- [ ] Test run successful
- [ ] Monitoring/logging set up
- [ ] Cost alerts configured

## Next Steps

1. **Deploy to Production** - Use stable GPU types (A40/A100)
2. **Set Up Monitoring** - Track job success/failure rates
3. **Configure Autoscaling** - Adjust min/max workers based on load
4. **Add Error Handling** - Implement retries and notifications

## Support

- **RunPod Docs:** https://docs.runpod.io/
- **RunPod Discord:** https://discord.gg/runpod
- **GCS Docs:** https://cloud.google.com/storage/docs

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│ CloudUpscaler Client (Your Machine)             │
│                                                 │
│  1. Create ZIP of images                       │
│  2. Upload to GCS                              │
│  3. Submit job to RunPod                       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ Google Cloud Storage                            │
│                                                 │
│  - input.zip (uploaded by client)              │
│  - output.zip (uploaded by handler)            │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ RunPod Serverless (GPU Workers)                 │
│                                                 │
│  Handler:                                       │
│  1. Download input.zip from GCS                │
│  2. Extract PNG files                          │
│  3. Upscale with Real-ESRGAN (GPU)             │
│  4. Create output.zip                          │
│  5. Upload to GCS                              │
│  6. Return signed URL                          │
└─────────────────────────────────────────────────┘
```
