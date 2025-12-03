"""
Image upscaling using Real-ESRGAN.
Uses PIL/Pillow instead of OpenCV to avoid OpenGL dependencies.
"""

import numpy as np
import torch
from PIL import Image
from pathlib import Path
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer


class ImageUpscaler:
    """Upscales images using Real-ESRGAN."""

    def __init__(self, model_name: str = "net_g_1000000", tile_size: int = 0, tile_pad: int = 10, gpu_id: int = 0, scale: int = 4, fp32: bool = False):
        """
        Initialize upscaler.

        Args:
            model_name: Name of the model to use
            tile_size: Tile size for processing (0 = no tiling)
            tile_pad: Padding for tiles (default 10, use 0 for no padding)
            gpu_id: GPU ID to use (0-indexed)
            scale: Upscaling factor (default: 4)
            fp32: Use FP32 precision instead of FP16 (default: False)
        """
        self.model_name = model_name
        self.tile_size = tile_size
        self.tile_pad = tile_pad
        self.gpu_id = gpu_id
        self.scale = scale
        self.model_path = f"/weights/{model_name}.pth"

        # Detect GPU availability
        use_gpu = torch.cuda.is_available()
        actual_gpu_id = gpu_id if use_gpu else None

        # Half precision: use FP16 unless fp32 is True
        # Note: FP16 can cause CUBLAS errors on some GPUs, so fp32=True is safer
        use_half = not fp32

        # Initialize model architecture
        self.model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=scale
        )

        # Create upsampler
        self.upsampler = RealESRGANer(
            scale=scale,
            model_path=self.model_path,
            model=self.model,
            tile=tile_size if tile_size > 0 else 0,
            tile_pad=tile_pad,
            pre_pad=0,
            half=use_half,
            gpu_id=actual_gpu_id
        )

    def upscale_directory(self, input_dir: Path, output_dir: Path) -> list[Path]:
        """
        Upscale all image files in a directory (PNG, JPG, JPEG).

        Args:
            input_dir: Directory containing image files
            output_dir: Directory to save upscaled files

        Returns:
            List of upscaled files
        """
        output_files = []

        # Process PNG, JPG, and JPEG files
        import itertools
        image_patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
        image_files = itertools.chain.from_iterable(input_dir.glob(pattern) for pattern in image_patterns)

        for png_file in image_files:
            # Load image with PIL
            pil_img = Image.open(png_file)

            # Convert to numpy array in BGR format (Real-ESRGAN expects BGR)
            img = np.array(pil_img)
            if img.ndim == 2:  # Grayscale
                img = np.stack([img, img, img], axis=2)
            elif img.shape[2] == 4:  # RGBA
                img = img[:, :, :3]  # Drop alpha channel

            # Convert RGB to BGR for Real-ESRGAN
            img = img[:, :, ::-1]

            # Upscale
            output, _ = self.upsampler.enhance(img, outscale=self.scale)

            # Convert BGR back to RGB
            output = output[:, :, ::-1]

            # Save with PIL
            output_file = output_dir / png_file.name
            Image.fromarray(output).save(output_file)
            output_files.append(output_file)

        return output_files
