#!/bin/bash
# Build and push Real-ESRGAN RunPod Serverless image

set -e  # Exit on error

# Configuration
IMAGE_NAME="iankonradjohnson/realesrgan-runpod"
VERSION="${1:-latest}"  # Default to 'latest' if no version specified

echo "🐳 Building Docker image for linux/amd64: ${IMAGE_NAME}:${VERSION}"
docker buildx build --platform linux/amd64 -t "${IMAGE_NAME}:${VERSION}" --load .

echo "✅ Build complete!"
echo ""
echo "📤 Push to Docker Hub with:"
echo "   docker push ${IMAGE_NAME}:${VERSION}"
echo ""
echo "🧪 Test locally with:"
echo "   docker run --gpus all -it ${IMAGE_NAME}:${VERSION} /bin/bash"
