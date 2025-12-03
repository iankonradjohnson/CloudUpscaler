#!/usr/bin/env python3
"""
CloudUpscaler CLI - Upscale images using Real-ESRGAN on cloud GPU.

Usage:
  # Local mode (simulation, no cloud):
  cloud-upscaler input_dir/ output_dir/

  # Cloud mode (requires env vars):
  export RUNPOD_API_KEY=your_key
  export RUNPOD_ENDPOINT_ID=your_endpoint
  export GCS_BUCKET=your_bucket
  export GCS_PROJECT_ID=your_project
  cloud-upscaler input_dir/ output_dir/ --cloud
"""

import sys
import os
from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Upscale images using Real-ESRGAN on cloud GPU',
        epilog='See MCP_SETUP.md for configuration details'
    )
    parser.add_argument('input_dir', type=Path, help='Input directory with image files (PNG, JPG, JPEG)')
    parser.add_argument('output_dir', type=Path, help='Output directory for upscaled files')
    parser.add_argument('--cloud', action='store_true', help='Use cloud processing (requires env vars)')
    parser.add_argument('--model', default='net_g_1000000', help='Model name (default: net_g_1000000)')
    parser.add_argument('--timeout', type=int, default=3600, help='Timeout in seconds (default: 3600)')

    # GCS/Cloud parameters
    parser.add_argument('--gcs-output-path', type=str, default='upscaled/output.zip',
                        help='GCS output path for cloud processing (default: upscaled/output.zip)')

    # Real-ESRGAN specific parameters
    parser.add_argument('--tile-size', type=int, default=0, help='Tile size for processing (0=auto, default: 0)')
    parser.add_argument('--scale', type=int, default=4, help='Upscaling factor (default: 4)')
    parser.add_argument('--face-enhance', action='store_true', help='Enable face enhancement (default: False)')
    parser.add_argument('--fp32', action='store_true', help='Use FP32 precision instead of FP16 (default: False)')
    parser.add_argument('--gpu-id', type=str, default='0', help='GPU device ID (default: "0")')

    args = parser.parse_args()

    from cloud_upscaler import upscale_images

    # Validate input directory
    if not args.input_dir.exists():
        print(f"Error: Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    # Create output directory if needed
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input:  {args.input_dir.absolute()}", flush=True)
    print(f"Output: {args.output_dir.absolute()}", flush=True)
    print(f"Mode:   {'Cloud' if args.cloud else 'Local (simulation)'}", flush=True)
    print(flush=True)

    # Count input files (PNG, JPG, JPEG)
    import itertools
    image_patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
    image_files = list(itertools.chain.from_iterable(
        args.input_dir.glob(pattern) for pattern in image_patterns
    ))
    print(f"Found {len(image_files)} image files", flush=True)

    # Setup providers if cloud mode
    storage_provider = None
    compute_provider = None

    if args.cloud:
        from cloud_upscaler.providers.gcs import GoogleCloudStorageProvider
        from cloud_upscaler.providers.runpod import RunPodComputeProvider

        # Get credentials from environment
        api_key = os.getenv('RUNPOD_API_KEY')
        endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
        bucket = os.getenv('GCS_BUCKET')
        project_id = os.getenv('GCS_PROJECT_ID')

        if not all([api_key, endpoint_id, bucket]):
            print("Error: Cloud mode requires environment variables:")
            print("  - RUNPOD_API_KEY")
            print("  - RUNPOD_ENDPOINT_ID")
            print("  - GCS_BUCKET")
            print("  - GCS_PROJECT_ID (optional)")
            sys.exit(1)

        print(f"RunPod Endpoint: {endpoint_id}", flush=True)
        print(f"GCS Bucket: {bucket}", flush=True)
        print(flush=True)

        storage_provider = GoogleCloudStorageProvider(bucket, project_id)
        compute_provider = RunPodComputeProvider(
            api_key=api_key,
            endpoint_id=endpoint_id,
            output_bucket=bucket,
            output_path=args.gcs_output_path
        )

    # Run upscaling
    print("Starting upscaling...", flush=True)

    # Build Real-ESRGAN parameters
    realesrgan_params = {
        'tile_size': args.tile_size,
        'scale': args.scale,
        'face_enhance': args.face_enhance,
        'fp32': args.fp32,
        'gpu_id': args.gpu_id
    }

    result = upscale_images(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        model_name=args.model,
        timeout_seconds=args.timeout,
        storage_provider=storage_provider,
        compute_provider=compute_provider,
        realesrgan_params=realesrgan_params
    )

    print(flush=True)
    if result.success:
        print(f"✓ SUCCESS: Processed {result.images_processed} images", flush=True)
        print(f"Output files saved to: {args.output_dir.absolute()}", flush=True)
    else:
        print(f"✗ FAILED: {result.error}", flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
