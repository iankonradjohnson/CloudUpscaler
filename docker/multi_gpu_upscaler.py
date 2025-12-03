"""
Multi-GPU batch image upscaling using concurrent processing.
"""

import os
import torch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from image_upscaler import ImageUpscaler


class MultiGPUUpscaler:
    """Process images in parallel across multiple GPUs."""

    def __init__(self, model_name: str, tile_size: int, tile_pad: int, gpu_count: int, scale: int = 4, fp32: bool = False):
        """
        Initialize multi-GPU upscaler.

        Args:
            model_name: Name of the model to use
            tile_size: Tile size for processing
            tile_pad: Padding for tiles
            gpu_count: Number of GPUs to use
            scale: Upscaling factor (default: 4)
            fp32: Use FP32 precision instead of FP16 (default: False)
        """
        self.model_name = model_name
        self.tile_size = tile_size
        self.tile_pad = tile_pad
        self.scale = scale

        # Detect available GPUs
        if torch.cuda.is_available():
            available_gpus = torch.cuda.device_count()
            self.gpu_count = min(gpu_count, available_gpus)
            print(f"Using {self.gpu_count} GPUs (requested: {gpu_count}, available: {available_gpus})")
        else:
            self.gpu_count = 0
            print("No GPUs available, using CPU")

        # Create one upscaler per GPU
        self.upscalers = []
        for gpu_id in range(self.gpu_count if self.gpu_count > 0 else 1):
            upscaler = ImageUpscaler(
                model_name=model_name,
                tile_size=tile_size,
                tile_pad=tile_pad,
                gpu_id=gpu_id,
                scale=scale,
                fp32=fp32
            )
            self.upscalers.append((gpu_id, upscaler))

    def upscale_directory(self, input_dir: Path, output_dir: Path) -> list[Path]:
        """
        Upscale all images in directory using multiple GPUs in parallel.

        Args:
            input_dir: Directory containing image files
            output_dir: Directory to save upscaled files

        Returns:
            List of upscaled files
        """
        # Collect all image files
        import itertools
        image_patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
        image_files = list(itertools.chain.from_iterable(
            input_dir.glob(pattern) for pattern in image_patterns
        ))

        if not image_files:
            return []

        print(f"Processing {len(image_files)} images across {self.gpu_count} GPU(s)")

        output_files = []

        # If only one GPU or CPU, process sequentially
        if self.gpu_count <= 1:
            gpu_id, upscaler = self.upscalers[0]
            for image_file in image_files:
                result = upscaler.upscale_directory(
                    Path(image_file).parent,
                    output_dir
                )
                output_files.extend(result)
            return output_files

        # Multi-GPU: Process images in parallel
        with ThreadPoolExecutor(max_workers=self.gpu_count) as executor:
            futures = []

            for i, image_file in enumerate(image_files):
                # Round-robin assignment to GPUs
                gpu_idx = i % self.gpu_count
                gpu_id, upscaler = self.upscalers[gpu_idx]

                # Submit task
                future = executor.submit(
                    self._process_single_image,
                    upscaler,
                    image_file,
                    output_dir,
                    gpu_id
                )
                futures.append(future)

            # Collect results
            for future in as_completed(futures):
                try:
                    output_file = future.result()
                    if output_file:
                        output_files.append(output_file)
                        print(f"Completed: {output_file.name}")
                except Exception as e:
                    print(f"Error processing image: {e}")

        return output_files

    def _process_single_image(
        self,
        upscaler: ImageUpscaler,
        image_file: Path,
        output_dir: Path,
        gpu_id: int
    ) -> Path:
        """
        Process a single image on a specific GPU.

        Args:
            upscaler: Upscaler instance for this GPU
            image_file: Input image file
            output_dir: Output directory
            gpu_id: GPU ID being used

        Returns:
            Output file path
        """
        # Create a temporary directory with just this file
        from PIL import Image
        import numpy as np

        # Load image
        pil_img = Image.open(image_file)

        # Convert to numpy array
        img = np.array(pil_img)
        if img.ndim == 2:  # Grayscale
            img = np.stack([img, img, img], axis=2)
        elif img.shape[2] == 4:  # RGBA
            img = img[:, :, :3]  # Drop alpha

        # Convert RGB to BGR
        img = img[:, :, ::-1]

        # Upscale
        output, _ = upscaler.upsampler.enhance(img, outscale=self.scale)

        # Convert BGR back to RGB
        output = output[:, :, ::-1]

        # Save
        output_file = output_dir / image_file.name
        Image.fromarray(output).save(output_file)

        return output_file
