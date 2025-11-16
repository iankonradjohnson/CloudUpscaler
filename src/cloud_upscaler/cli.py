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
        description='Upscale PNG images using Real-ESRGAN on cloud GPU',
        epilog='See MCP_SETUP.md for configuration details'
    )
    parser.add_argument('input_dir', type=Path, help='Input directory with PNG files')
    parser.add_argument('output_dir', type=Path, help='Output directory for upscaled files')
    parser.add_argument('--cloud', action='store_true', help='Use cloud processing (requires env vars)')
    parser.add_argument('--model', default='net_g_1000000', help='Model name (default: net_g_1000000)')
    parser.add_argument('--timeout', type=int, default=3600, help='Timeout in seconds (default: 3600)')

    args = parser.parse_args()

    from cloud_upscaler import upscale_images

    # Validate input directory
    if not args.input_dir.exists():
        print(f"Error: Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    # Create output directory if needed
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input:  {args.input_dir.absolute()}")
    print(f"Output: {args.output_dir.absolute()}")
    print(f"Mode:   {'Cloud' if args.cloud else 'Local (simulation)'}")
    print()

    # Count input files
    png_files = list(args.input_dir.glob("*.png"))
    print(f"Found {len(png_files)} PNG files")

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

        print(f"RunPod Endpoint: {endpoint_id}")
        print(f"GCS Bucket: {bucket}")
        print()

        storage_provider = GoogleCloudStorageProvider(bucket, project_id)
        compute_provider = RunPodComputeProvider(
            api_key=api_key,
            endpoint_id=endpoint_id,
            output_bucket=bucket,
            output_path="upscaled/output.zip"
        )

    # Run upscaling
    print("Starting upscaling...")
    result = upscale_images(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        model_name=args.model,
        timeout_seconds=args.timeout,
        storage_provider=storage_provider,
        compute_provider=compute_provider
    )

    print()
    if result.success:
        print(f"✓ SUCCESS: Processed {result.images_processed} images")
        print(f"Output files saved to: {args.output_dir.absolute()}")
    else:
        print(f"✗ FAILED: {result.error}")
        sys.exit(1)


if __name__ == '__main__':
    main()
