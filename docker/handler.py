"""
RunPod Serverless handler for Real-ESRGAN image upscaling.
"""

import requests
import tempfile
import zipfile
from pathlib import Path
from google.cloud import storage
import cv2
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from zip_extractor import ZipExtractor
from zip_creator import ZipCreator
from image_upscaler import ImageUpscaler
from cloud_storage import CloudStorage
from image_downloader import ImageDownloader


def handler(job):
    """
    RunPod serverless handler.

    This is called by RunPod for each job.
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

        # Extract parameters
        input_url = job_input['input_url']
        output_bucket = job_input['output_bucket']
        output_path = job_input['output_path']

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download input ZIP
            input_zip_path = temp_path / "input.zip"
            downloader = ImageDownloader()
            downloader.download(input_url, input_zip_path)

            # Extract input files
            input_dir = temp_path / "input"
            input_dir.mkdir()
            extractor = ZipExtractor()
            extractor.extract(input_zip_path, input_dir)

            # Upscale images with Real-ESRGAN
            output_dir = temp_path / "output"
            output_dir.mkdir()

            model_name = job_input.get('model_name', 'net_g_1000000')
            tile_size = job_input.get('tile_size', 0)

            upscaler = ImageUpscaler(model_name=model_name, tile_size=tile_size)
            upscaler.upscale_directory(input_dir, output_dir)

            # Create output ZIP
            output_zip_path = temp_path / "output.zip"
            output_files = list(output_dir.glob("*.png"))
            creator = ZipCreator()
            creator.create(output_files, output_zip_path)

            # Upload to GCS
            cloud = CloudStorage()
            output_url = cloud.upload_and_get_url(output_zip_path, output_bucket, output_path)

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
    runpod.serverless.start({"handler": handler})
