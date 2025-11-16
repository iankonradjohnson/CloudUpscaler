"""
RunPod Serverless handler for Real-ESRGAN image upscaling.
"""

import os
import json
import tempfile
from pathlib import Path
from zip_extractor import ZipExtractor
from zip_creator import ZipCreator
from image_upscaler import ImageUpscaler
from multi_gpu_upscaler import MultiGPUUpscaler
from cloud_storage import CloudStorage
from image_downloader import ImageDownloader


class Handler:
    """RunPod serverless handler with dependency injection."""

    def __init__(
        self,
        downloader: ImageDownloader,
        extractor: ZipExtractor,
        upscaler: ImageUpscaler,
        creator: ZipCreator,
        storage: CloudStorage
    ):
        """
        Initialize handler with dependencies.

        Args:
            downloader: Downloads files from URLs
            extractor: Extracts ZIP files
            upscaler: Upscaler instance (can be None if created per-job)
            creator: Creates ZIP files
            storage: Uploads to cloud storage
        """
        self.downloader = downloader
        self.extractor = extractor
        self.upscaler = upscaler  # Can be None if created per-job
        self.creator = creator
        self.storage = storage

    def handle(self, job):
        """
        Handle RunPod job.

        Args:
            job: RunPod job dict with 'input' key

        Returns:
            Dict with 'output' or 'error' key
        """
        try:
            job_input = job['input']

            # Validate required fields
            required_fields = ['input_url', 'output_bucket', 'output_path']
            for field in required_fields:
                if field not in job_input:
                    return {
                        'error': f'Missing required field: {field}'
                    }

            # Extract and validate Real-ESRGAN parameters
            tile_size = job_input.get('tile_size', 0)
            tile_pad = job_input.get('tile_pad', 10)  # Real-ESRGAN default
            gpu_count = job_input.get('gpu_count', 1)
            model_name = job_input.get('model_name', 'net_g_1000000')

            # Validate tile_size (Real-ESRGAN spec: must be 0 or >= 32)
            if tile_size != 0 and tile_size < 32:
                return {
                    'error': f'Invalid tile_size: {tile_size}. Must be 0 (no tiling) or >= 32 (minimum per Real-ESRGAN spec)'
                }

            # Extract job parameters
            input_url = job_input['input_url']
            output_bucket = job_input['output_bucket']
            output_path = job_input['output_path']

            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Download input ZIP
                input_zip_path = temp_path / "input.zip"
                self.downloader.download(input_url, input_zip_path)

                # Extract input files
                input_dir = temp_path / "input"
                input_dir.mkdir()
                self.extractor.extract(input_zip_path, input_dir)

                # Create upscaler with job-specific parameters
                if gpu_count > 1:
                    # Use multi-GPU upscaler for parallel processing
                    upscaler = MultiGPUUpscaler(
                        model_name=model_name,
                        tile_size=tile_size,
                        tile_pad=tile_pad,
                        gpu_count=gpu_count
                    )
                else:
                    # Use single-GPU upscaler (or fallback injected upscaler)
                    if self.upscaler is None:
                        upscaler = ImageUpscaler(
                            model_name=model_name,
                            tile_size=tile_size,
                            tile_pad=tile_pad,
                            gpu_id=0
                        )
                    else:
                        # Use pre-injected upscaler (for testing)
                        upscaler = self.upscaler

                # Upscale images with Real-ESRGAN
                output_dir = temp_path / "output"
                output_dir.mkdir()
                upscaler.upscale_directory(input_dir, output_dir)

                # Create output ZIP
                output_zip_path = temp_path / "output.zip"
                # Collect all image files (PNG, JPG, JPEG)
                output_files = []
                for pattern in ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]:
                    output_files.extend(output_dir.glob(pattern))
                self.creator.create(output_files, output_zip_path)

                # Upload to GCS
                output_url = self.storage.upload_and_get_url(
                    output_zip_path, output_bucket, output_path
                )

                return {
                    'output': {
                        'output_url': output_url
                    }
                }

        except Exception as e:
            return {
                'error': str(e)
            }


# Start RunPod serverless handler
if __name__ == "__main__":
    import runpod

    # Setup GCS credentials from environment variable if provided
    gcs_creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if gcs_creds_json:
        # Write credentials to file
        creds_path = '/tmp/gcs_credentials.json'
        with open(creds_path, 'w') as f:
            # Handle both string and already-parsed dict
            if isinstance(gcs_creds_json, str):
                f.write(gcs_creds_json)
            else:
                json.dump(gcs_creds_json, f)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
        print(f"✓ GCS credentials loaded from environment variable")

    # Create dependencies
    model_name = 'net_g_1000000'
    tile_size = 0

    handler = Handler(
        downloader=ImageDownloader(),
        extractor=ZipExtractor(),
        upscaler=ImageUpscaler(model_name=model_name, tile_size=tile_size),
        creator=ZipCreator(),
        storage=CloudStorage()
    )

    runpod.serverless.start({"handler": handler.handle})
