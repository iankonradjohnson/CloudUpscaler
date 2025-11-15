"""
Image upscaling using Real-ESRGAN.
"""

import cv2
from pathlib import Path
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer


class ImageUpscaler:
    """Upscales images using Real-ESRGAN."""

    def __init__(self, model_name: str = "net_g_1000000", tile_size: int = 0):
        """
        Initialize upscaler.

        Args:
            model_name: Name of the model to use
            tile_size: Tile size for processing (0 = no tiling)
        """
        self.model_name = model_name
        self.tile_size = tile_size
        self.model_path = f"/weights/{model_name}.pth"

        # Initialize model architecture
        self.model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=4
        )

        # Create upsampler
        self.upsampler = RealESRGANer(
            scale=4,
            model_path=self.model_path,
            model=self.model,
            tile=tile_size if tile_size > 0 else 0,
            tile_pad=10,
            pre_pad=0,
            half=True,
            gpu_id=0
        )

    def upscale_directory(self, input_dir: Path, output_dir: Path) -> list[Path]:
        """
        Upscale all PNG files in a directory.

        Args:
            input_dir: Directory containing PNG files
            output_dir: Directory to save upscaled files

        Returns:
            List of upscaled files
        """
        output_files = []

        for png_file in input_dir.glob("*.png"):
            img = cv2.imread(str(png_file), cv2.IMREAD_UNCHANGED)
            if img is not None:
                output, _ = self.upsampler.enhance(img, outscale=4)
                output_file = output_dir / png_file.name
                cv2.imwrite(str(output_file), output)
                output_files.append(output_file)

        return output_files
