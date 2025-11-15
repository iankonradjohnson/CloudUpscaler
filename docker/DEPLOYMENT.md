# RunPod Serverless Deployment Guide

This guide walks through deploying the CloudUpscaler Real-ESRGAN handler to RunPod Serverless.

## Prerequisites

1. **Docker** installed locally
2. **RunPod account** with credits
3. **Docker Hub account** (or other container registry)
4. **Google Cloud Storage** bucket with service account credentials

## Step 1: Build Docker Image

```bash
cd docker/
docker build -t your-username/realesrgan-runpod:latest .
```

This will:
- Install CUDA 11.8 runtime
- Install PyTorch with GPU support
- Install Real-ESRGAN and dependencies
- Download default model weights (RealESRGAN_x4plus, net_g_1000000)
- Copy the handler

Build time: ~10-15 minutes

## Step 2: Test Locally (Optional)

Test the handler locally with RunPod's test runner:

```bash
docker run --gpus all -it your-username/realesrgan-runpod:latest python -c "
from handler import handler
import json

# Test payload
job = {
    'input': {
        'input_url': 'https://storage.googleapis.com/your-bucket/test-input.zip',
        'output_bucket': 'your-bucket',
        'output_path': 'test-output/result.zip',
        'model_name': 'net_g_1000000',
        'tile_size': 0,
        'gpu_count': 1
    }
}

result = handler(job)
print(json.dumps(result, indent=2))
"
```

**Note:** Requires valid GCS credentials and signed URLs.

## Step 3: Push to Container Registry

```bash
docker login
docker push your-username/realesrgan-runpod:latest
```

## Step 4: Create RunPod Serverless Endpoint

### Via RunPod Web UI:

1. Go to https://www.runpod.io/console/serverless
2. Click **"New Endpoint"**
3. Configure:
   - **Endpoint Name:** `realesrgan-upscaler`
   - **Docker Image:** `your-username/realesrgan-runpod:latest`
   - **GPU Type:** RTX 3090 or better (recommended)
   - **Container Disk:** 20GB minimum
   - **Max Workers:** 3 (adjust based on usage)
   - **Idle Timeout:** 5 seconds
   - **Active Workers:** 0 (serverless, scales to zero)

4. **Environment Variables:**
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs_credentials.json
   ```

5. Click **"Deploy"**

### Via RunPod API (Alternative):

```bash
curl -X POST https://api.runpod.ai/v2/endpoints \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "realesrgan-upscaler",
    "image": "your-username/realesrgan-runpod:latest",
    "gpu_type": "NVIDIA RTX 3090",
    "container_disk_in_gb": 20,
    "env": {
      "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/gcs_credentials.json"
    }
  }'
```

## Step 5: Configure GCS Credentials

The handler needs Google Cloud Storage credentials to upload/download files.

**Option A: Include credentials in Docker image** (Not recommended for security)

**Option B: Use RunPod Secrets** (Recommended)
1. In RunPod console, go to Settings → Secrets
2. Add secret: `GCS_CREDENTIALS` with your service account JSON
3. Mount in endpoint config

**Option C: Use signed URLs only**
- Client generates signed URLs for input/output
- Handler doesn't need credentials (simpler, more secure)

## Step 6: Get Endpoint ID

After deployment, RunPod will provide:
- **Endpoint ID:** `abc123def456` (use this in CloudUpscaler client)
- **Endpoint URL:** `https://api.runpod.ai/v2/abc123def456`

Copy the Endpoint ID for your `.env` file.

## Step 7: Update Client Configuration

In your CloudUpscaler project:

```bash
# .env
RUNPOD_API_KEY=your-runpod-api-key
RUNPOD_ENDPOINT_ID=abc123def456  # From Step 6
RUNPOD_OUTPUT_BUCKET=your-gcs-bucket
RUNPOD_OUTPUT_PATH=outputs/upscaled
GCS_BUCKET_NAME=your-gcs-bucket
GCS_PROJECT_ID=your-gcp-project
```

## Step 8: Test End-to-End

```python
from cloud_upscaler.mcp_tool import upscale_images_sync

result = upscale_images_sync(
    image_dir="/path/to/input/images",
    output_dir="/path/to/output"
)

print(result)
# {'success': True, 'images_processed': 10, 'error': None}
```

## Monitoring

### View Logs:
```bash
# Via RunPod CLI
runpod logs <endpoint-id>

# Or in RunPod web console:
# Serverless → Your Endpoint → Logs
```

### Check Job Status:
```bash
curl https://api.runpod.ai/v2/abc123def456/status/JOB_ID \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Troubleshooting

### Build fails with CUDA errors:
- Ensure base image matches RunPod GPU runtime
- Try `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`

### Handler crashes with "out of memory":
- Increase `tile_size` in job payload (try 256, 512)
- Use smaller GPU workers
- Process fewer images per batch

### GCS upload fails:
- Verify service account has Storage Object Admin role
- Check bucket permissions
- Ensure credentials are correctly mounted

### Slow cold starts:
- Image size too large - optimize layers
- Increase "Container Disk" size
- Pre-warm with minimum active workers

## Cost Optimization

- **Idle Timeout:** Set to 5s to scale to zero quickly
- **Active Workers:** Keep at 0 for true serverless
- **GPU Type:** RTX 3090 offers best price/performance for Real-ESRGAN
- **Spot Instances:** Enable for ~70% cost savings (may interrupt)

## Model Customization

To use custom Real-ESRGAN models:

1. Add model weights to Docker image:
```dockerfile
# In Dockerfile
RUN wget YOUR_MODEL_URL -O /weights/custom_model.pth
```

2. Rebuild and redeploy:
```bash
docker build -t your-username/realesrgan-runpod:v2 .
docker push your-username/realesrgan-runpod:v2
```

3. Update RunPod endpoint to use new image

4. Pass model name in job payload:
```json
{
  "input": {
    "model_name": "custom_model",
    ...
  }
}
```

## Next Steps

- Set up monitoring and alerting
- Implement retries for failed jobs
- Add support for video upscaling
- Optimize model inference speed
- Deploy to multiple regions
