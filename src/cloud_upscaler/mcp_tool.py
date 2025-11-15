"""
MCP tool wrapper for CloudUpscaler.

This module provides a synchronous MCP-compatible interface for upscaling images.
"""

import os
from pathlib import Path
from cloud_upscaler import upscale_images
from cloud_upscaler.providers.runpod import RunPodComputeProvider
from cloud_upscaler.providers.gcs import GoogleCloudStorageProvider


def upscale_images_sync(image_dir: str, output_dir: str) -> dict:
    """
    Upscale images using RunPod and Google Cloud Storage.

    This is an MCP-compatible synchronous wrapper that:
    1. Reads credentials from environment variables
    2. Initializes real providers
    3. Calls upscale_images()
    4. Returns a simple dictionary result

    Args:
        image_dir: Path to directory containing PNG images
        output_dir: Path to directory for upscaled images

    Returns:
        Dict with keys: success (bool), images_processed (int), error (str or None)

    Environment variables required:
        RUNPOD_API_KEY: RunPod API key
        RUNPOD_ENDPOINT_ID: RunPod endpoint ID
        GCS_BUCKET_NAME: Google Cloud Storage bucket name
        GCS_PROJECT_ID: Google Cloud project ID
    """
    # Get credentials from environment
    runpod_api_key = os.environ['RUNPOD_API_KEY']
    runpod_endpoint_id = os.environ['RUNPOD_ENDPOINT_ID']
    gcs_bucket_name = os.environ['GCS_BUCKET_NAME']
    gcs_project_id = os.environ['GCS_PROJECT_ID']

    # Initialize providers
    compute_provider = RunPodComputeProvider(
        api_key=runpod_api_key,
        endpoint_id=runpod_endpoint_id
    )
    storage_provider = GoogleCloudStorageProvider(
        bucket_name=gcs_bucket_name,
        project_id=gcs_project_id
    )

    # Call upscale_images
    result = upscale_images(
        input_dir=Path(image_dir),
        output_dir=Path(output_dir),
        storage_provider=storage_provider,
        compute_provider=compute_provider
    )

    # Return MCP-compatible dictionary
    return {
        'success': result.success,
        'images_processed': result.images_processed,
        'error': result.error
    }
