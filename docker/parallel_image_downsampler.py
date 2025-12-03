"""
Parallel image downsampling using PIL.
"""

import os
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor


class ParallelImageDownsampler:
    """Downsample images in parallel using PIL."""

    def downsample_directory(self, image_dir: Path, scale: float, max_workers: int = None) -> list[Path]:
        """
        Downsample all images in directory by scale factor.

        Args:
            image_dir: Directory containing images to downsample
            scale: Scale factor (0.1 to 1.0)
            max_workers: Number of parallel workers (default: CPU count)

        Returns:
            List of downsampled image paths
        """
        # Default to CPU count for max parallelism
        if max_workers is None:
            max_workers = os.cpu_count() or 4

        # Find all image files
        image_patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
        image_files = []
        for pattern in image_patterns:
            image_files.extend(image_dir.glob(pattern))

        # Process images in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self._downsample_image, img_path, scale)
                for img_path in image_files
            ]
            # Wait for all to complete
            results = [future.result() for future in futures]

        return results

    def _downsample_image(self, image_path: Path, scale: float) -> Path:
        """
        Downsample a single image and overwrite the original.

        Args:
            image_path: Path to image file
            scale: Scale factor (0.1 to 1.0)

        Returns:
            Path to downsampled image (same as input)
        """
        # Disable PIL's decompression bomb check for large upscaled images
        # Our images are legitimately large (4x upscaled), not attacks
        Image.MAX_IMAGE_PIXELS = None

        # Load image
        img = Image.open(image_path)

        # Calculate new dimensions
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)

        # Resize with high-quality Lanczos filter
        downsampled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save back to same path (overwrite)
        downsampled.save(image_path)

        return image_path
