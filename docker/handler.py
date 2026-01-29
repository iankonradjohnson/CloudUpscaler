"""
RunPod Serverless handler for Real-ESRGAN image upscaling.
"""

import os
import json
import tempfile
import traceback
import logging
from pathlib import Path
from zip_extractor import ZipExtractor
from zip_creator import ZipCreator
from image_upscaler import ImageUpscaler
from multi_gpu_upscaler import MultiGPUUpscaler
from cloud_storage import CloudStorage
from image_downloader import ImageDownloader
from parallel_image_downsampler import ParallelImageDownsampler

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


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

                # Upscale and upload in batches for progressive streaming
                output_dir = temp_path / "output"
                output_dir.mkdir()

                # Collect all input image files
                import itertools
                image_patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
                input_files = list(itertools.chain.from_iterable(
                    input_dir.glob(pattern) for pattern in image_patterns
                ))

                print(f"\n{'='*60}", flush=True)
                print(f"🎨 UPSCALING AND UPLOADING IN BATCHES", flush=True)
                print(f"   Total images: {len(input_files)}", flush=True)
                print(f"   Batch size: 10 images", flush=True)
                print(f"   Destination: gs://{output_bucket}/{output_path.replace('.zip', '')}", flush=True)
                print(f"{'='*60}\n", flush=True)

                # Process in batches of 10 with background uploading
                import queue
                import threading
                from concurrent.futures import ThreadPoolExecutor

                batch_size = 10
                gcs_prefix = output_path.replace('.zip', '')
                all_image_urls = []
                all_urls_lock = threading.Lock()
                upload_queue = queue.Queue()

                # Upload worker thread
                def upload_worker():
                    """Background worker that processes upload queue."""
                    while True:
                        item = upload_queue.get()

                        if item is None:  # Poison pill
                            upload_queue.task_done()
                            break

                        batch_num, batch_files = item

                        try:
                            print(f"   📤 Uploading batch {batch_num} in background... ({len(batch_files)} images)", flush=True)

                            def upload_image(args):
                                idx, output_file = args
                                gcs_url = self.storage.upload_and_get_url(
                                    output_file,
                                    output_bucket,
                                    f"{gcs_prefix}/{output_file.name}"
                                )
                                return gcs_url

                            with ThreadPoolExecutor(max_workers=10) as executor:
                                urls = list(executor.map(upload_image, enumerate(batch_files)))

                            with all_urls_lock:
                                all_image_urls.extend(urls)

                            print(f"   ✅ Batch {batch_num} uploaded ({len(urls)} images, total: {len(all_image_urls)})", flush=True)

                        except Exception as e:
                            print(f"   ❌ Upload batch {batch_num} failed: {str(e)}", flush=True)
                            raise
                        finally:
                            upload_queue.task_done()

                # Start upload worker thread
                worker_thread = threading.Thread(target=upload_worker)
                worker_thread.start()
                print(f"🚀 Upload worker thread started\n", flush=True)

                # Check which files already exist in GCS (for resume)
                print(f"🔍 Checking GCS for existing files...", flush=True)
                from google.cloud import storage
                gcs_client = storage.Client()
                gcs_bucket = gcs_client.bucket(output_bucket)

                existing_files = set()
                blobs = gcs_bucket.list_blobs(prefix=gcs_prefix)
                for blob in blobs:
                    filename = Path(blob.name).name
                    existing_files.add(filename)

                print(f"   Found {len(existing_files)} existing files in GCS", flush=True)

                # Filter out files that already exist
                files_to_process = [f for f in input_files if f.name not in existing_files]
                skipped_count = len(input_files) - len(files_to_process)

                if skipped_count > 0:
                    print(f"   ⏭️  Skipping {skipped_count} files that already exist", flush=True)
                    # Add existing files to URL list
                    for filename in existing_files:
                        if any(f.name == filename for f in input_files):
                            with all_urls_lock:
                                all_image_urls.append(f"gs://{output_bucket}/{gcs_prefix}/{filename}")

                print(f"   Processing {len(files_to_process)} remaining files", flush=True)

                # Process batches (upscale + downsample, then queue upload)
                total_batches = (len(files_to_process) + batch_size - 1) // batch_size

                for batch_idx in range(0, len(files_to_process), batch_size):
                    batch_files = files_to_process[batch_idx:batch_idx + batch_size]
                    batch_num = (batch_idx // batch_size) + 1

                    print(f"\n📦 BATCH {batch_num}/{total_batches} ({len(batch_files)} images)", flush=True)
                    print(f"   Upscaling...", flush=True)

                    # Upscale this batch
                    from PIL import Image
                    import numpy as np

                    batch_output_files = []
                    for img_file in batch_files:
                        pil_img = Image.open(img_file)
                        img = np.array(pil_img)
                        if img.ndim == 2:
                            img = np.stack([img, img, img], axis=2)
                        elif img.shape[2] == 4:
                            img = img[:, :, :3]

                        img = img[:, :, ::-1]  # RGB to BGR
                        output, _ = upscaler.upsampler.enhance(img, outscale=scale)
                        output = output[:, :, ::-1]  # BGR to RGB

                        output_file = output_dir / img_file.name
                        Image.fromarray(output).save(output_file)
                        batch_output_files.append(output_file)

                    print(f"   ✓ Upscaled {len(batch_output_files)} images", flush=True)

                    # Downsample if needed
                    if downsample_scale < 1.0:
                        print(f"   Downsampling to {downsample_scale}x... (parallel)", flush=True)
                        from PIL import Image as PILImage
                        PILImage.MAX_IMAGE_PIXELS = None

                        def downsample_image(args):
                            idx, output_file = args
                            img = Image.open(output_file)
                            new_size = (int(img.width * downsample_scale), int(img.height * downsample_scale))
                            img = img.resize(new_size, Image.LANCZOS)
                            img.save(output_file)

                        with ThreadPoolExecutor(max_workers=10) as executor:
                            list(executor.map(downsample_image, enumerate(batch_output_files)))

                        print(f"   ✓ Downsampled {len(batch_output_files)} images", flush=True)

                    # Queue batch for background upload
                    upload_queue.put((batch_num, batch_output_files))
                    print(f"   🔄 Batch {batch_num} queued for upload, continuing to next batch...", flush=True)

                # Signal worker to stop and wait for completion
                print(f"\n⏳ All batches processed, waiting for uploads to complete...", flush=True)
                upload_queue.put(None)  # Poison pill
                upload_queue.join()
                worker_thread.join()
                print(f"✅ Upload worker finished", flush=True)

                print(f"\n{'='*60}", flush=True)
                print(f"✅ ALL BATCHES COMPLETE", flush=True)
                print(f"   Total images processed: {len(all_image_urls)}", flush=True)
                print(f"{'='*60}\n", flush=True)

                image_urls = all_image_urls

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
