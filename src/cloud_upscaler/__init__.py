"""
CloudUpscaler - Upscale images using cloud GPU processing.
"""

from pathlib import Path


def upscale_images(input_dir: Path, output_dir: Path):
    """Upscale images from input_dir to output_dir"""
    if not input_dir.exists():
        raise ValueError("Input directory does not exist")
