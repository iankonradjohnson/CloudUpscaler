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
            response = requests.get(input_url)
            response.raise_for_status()

            input_zip_path = temp_path / "input.zip"
            input_zip_path.write_bytes(response.content)

            # Extract input files
            input_dir = temp_path / "input"
            input_dir.mkdir()
            with zipfile.ZipFile(input_zip_path, 'r') as zf:
                zf.extractall(input_dir)

            # Upscale images with Real-ESRGAN
            output_dir = temp_path / "output"
            output_dir.mkdir()

            model_name = job_input.get('model_name', 'net_g_1000000')
            model_path = f"/weights/{model_name}.pth"

            # Initialize model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)

            # Create upsampler
            tile_size = job_input.get('tile_size', 0)
            upsampler = RealESRGANer(
                scale=4,
                model_path=model_path,
                model=model,
                tile=tile_size if tile_size > 0 else 0,
                tile_pad=10,
                pre_pad=0,
                half=True,
                gpu_id=0
            )

            # Process each PNG file
            for png_file in input_dir.glob("*.png"):
                img = cv2.imread(str(png_file), cv2.IMREAD_UNCHANGED)
                if img is not None:
                    output, _ = upsampler.enhance(img, outscale=4)
                    output_file = output_dir / png_file.name
                    cv2.imwrite(str(output_file), output)

            return {
                'output': {}
            }

    except Exception as e:
        return {
            'error': str(e)
        }
