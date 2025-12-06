"""
RunPod Serverless handler for Real-ESRGAN image upscaling.
"""

import os
import json
import tempfile
import traceback
from pathlib import Path
from zip_extractor import ZipExtractor
from zip_creator import ZipCreator
from image_upscaler import ImageUpscaler
from multi_gpu_upscaler import MultiGPUUpscaler
from cloud_storage import CloudStorage
from image_downloader import ImageDownloader
from parallel_image_downsampler import ParallelImageDownsampler


class Handler:
    """RunPod serverless handler with dependency injection."""

    def __init__(
        self,
        downloader: ImageDownloader,
        extractor: ZipExtractor,
        upscaler: ImageUpscaler,
        creator: ZipCreator,
        storage: CloudStorage,
        downsampler: ParallelImageDownsampler
    ):
        """
        Initialize handler with dependencies.

        Args:
            downloader: Downloads files from URLs
            extractor: Extracts ZIP files
            upscaler: Upscaler instance (can be None if created per-job)
            creator: Creates ZIP files
            storage: Uploads to cloud storage
            downsampler: Downsamples images after upscaling
        """
        self.downloader = downloader
        self.extractor = extractor
        self.upscaler = upscaler  # Can be None if created per-job
        self.creator = creator
        self.storage = storage
        self.downsampler = downsampler

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
            scale = job_input.get('scale', 4)
            fp32 = job_input.get('fp32', False)
            gpu_id = job_input.get('gpu_id', '0')
            downsample_scale = job_input.get('downsample_scale', 1.0)

            # Convert gpu_id to int if it's a string
            if isinstance(gpu_id, str):
                gpu_id = int(gpu_id)

            # Validate tile_size (Real-ESRGAN spec: must be 0 or >= 32)
            if tile_size != 0 and tile_size < 32:
                return {
                    'error': f'Invalid tile_size: {tile_size}. Must be 0 (no tiling) or >= 32 (minimum per Real-ESRGAN spec)'
                }

            # Validate scale
            if scale not in [2, 4]:
                return {
                    'error': f'Invalid scale: {scale}. Must be 2 or 4'
                }

            # Validate downsample_scale
            if downsample_scale < 0.1 or downsample_scale > 1.0:
                return {
                    'error': f'Invalid downsample_scale: {downsample_scale}. Must be between 0.1 and 1.0'
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
                        gpu_count=gpu_count,
                        scale=scale,
                        fp32=fp32
                    )
                else:
                    # Use single-GPU upscaler (or fallback injected upscaler)
                    if self.upscaler is None:
                        upscaler = ImageUpscaler(
                            model_name=model_name,
                            tile_size=tile_size,
                            tile_pad=tile_pad,
                            gpu_id=gpu_id,
                            scale=scale,
                            fp32=fp32
                        )
                    else:
                        # Use pre-injected upscaler (for testing)
                        upscaler = self.upscaler

                # Upscale images with Real-ESRGAN
                output_dir = temp_path / "output"
                output_dir.mkdir()
                upscaler.upscale_directory(input_dir, output_dir)

                # Downsample if needed
                if downsample_scale < 1.0:
                    self.downsampler.downsample_directory(output_dir, downsample_scale)

                # Collect all image files (PNG, JPG, JPEG)
                output_files = []
                for pattern in ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]:
                    output_files.extend(output_dir.glob(pattern))

                # Upload images individually using StreamingImageUploader
                from streaming_uploader import StreamingImageUploader
                uploader = StreamingImageUploader.create_default(
                    storage_client=self.storage,
                    batch_size=10
                )
                gcs_prefix = output_path.replace('.zip', '')
                image_urls = uploader.upload_images_streaming(
                    image_paths=output_files,
                    bucket=output_bucket,
                    gcs_prefix=gcs_prefix
                )

                return {
                    'output': {
                        'image_urls': image_urls,
                        'image_count': len(image_urls),
                        'gcs_prefix': gcs_prefix
                    }
                }

        except Exception as e:
            # Log error to GCS for debugging
            error_msg = f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            try:
                # Write error log to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(error_msg)
                    error_log_path = f.name

                # Upload error log to GCS
                output_bucket = job_input.get('output_bucket', 'cloud-upscaler-test')
                output_path = job_input.get('output_path', 'error.log')
                error_path = output_path.replace('output.zip', 'error.log')

                self.storage.upload_and_get_url(
                    Path(error_log_path),
                    output_bucket,
                    error_path
                )
            except:
                pass  # Don't fail on error logging

            return {
                'error': str(e)
            }


# Start RunPod serverless handler
if __name__ == "__main__":
    import runpod

    # GCS credentials are embedded in the Docker image at /app/gcs_credentials.json
    # The GOOGLE_APPLICATION_CREDENTIALS env var is set in Dockerfile
    print(f"✓ Using GCS credentials from {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

    # Create dependencies
    model_name = 'net_g_1000000'
    tile_size = 256  # Use tiling to avoid GPU memory issues

    handler = Handler(
        downloader=ImageDownloader(),
        extractor=ZipExtractor(),
        upscaler=ImageUpscaler(model_name=model_name, tile_size=tile_size),
        creator=ZipCreator(),
        storage=CloudStorage(),
        downsampler=ParallelImageDownsampler()
    )

    runpod.serverless.start({"handler": handler.handle})
