# RunPod Serverless Docker image for Real-ESRGAN upscaling
# Based on NVIDIA CUDA for GPU support

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Upgrade pip
RUN pip install --upgrade pip

# Install PyTorch with CUDA 11.8 support
RUN pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118

# Install Real-ESRGAN dependencies
RUN pip install \
    basicsr==1.4.2 \
    facexlib==0.3.0 \
    gfpgan==1.3.8 \
    opencv-python==4.8.1.78 \
    realesrgan==0.3.0

# Install cloud and serverless dependencies
RUN pip install \
    google-cloud-storage==2.10.0 \
    runpod==1.6.2 \
    requests==2.31.0

# Create directories
RUN mkdir -p /weights /app

# Clone Real-ESRGAN repo for utilities
WORKDIR /
RUN git clone https://github.com/xinntao/Real-ESRGAN.git

# Download default model weights
WORKDIR /weights
RUN wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth -O RealESRGAN_x4plus.pth
RUN wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth -O net_g_1000000.pth

# Copy handler
WORKDIR /app
COPY handler.py /app/

# Set Google Cloud credentials path (will be set at runtime via env var)
ENV GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs_credentials.json

# RunPod serverless entrypoint
CMD ["python", "-u", "handler.py"]
