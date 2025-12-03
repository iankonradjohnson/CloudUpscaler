"""
Tests for ParallelImageDownsampler.

Testing approach:
- Use REAL PIL images (small test images for speed)
- Use REAL file system (tmp_path)
- NO mocking (test actual behavior)
"""

import pytest
from pathlib import Path
from PIL import Image
import sys

# Add docker directory to path
docker_dir = Path(__file__).parent.parent / 'docker'
sys.path.insert(0, str(docker_dir))

from parallel_image_downsampler import ParallelImageDownsampler


class TestParallelImageDownsampler:

    def test_downsamples_single_image_to_correct_dimensions(self, tmp_path):
        """
        Given: 100x100 image
        When: downsample at 0.5
        Then: 50x50 image
        """
        # Given: 100x100 image
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        test_img = Image.new('RGB', (100, 100), color='red')
        img_path = img_dir / "test.png"
        test_img.save(img_path)

        # When: downsample at 0.5
        downsampler = ParallelImageDownsampler()
        downsampler.downsample_directory(img_dir, scale=0.5)

        # Then: 50x50 image
        result_img = Image.open(img_path)
        assert result_img.size == (50, 50), f"Expected (50, 50), got {result_img.size}"

    def test_downsamples_multiple_images(self, tmp_path):
        """
        Given: 3 images (100x100)
        When: downsample at 0.8
        Then: all 3 images are 80x80
        """
        # Given: 3 images (100x100)
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        for i in range(3):
            test_img = Image.new('RGB', (100, 100), color='blue')
            test_img.save(img_dir / f"test{i}.png")

        # When: downsample at 0.8
        downsampler = ParallelImageDownsampler()
        downsampler.downsample_directory(img_dir, scale=0.8)

        # Then: all 3 images are 80x80
        for i in range(3):
            result_img = Image.open(img_dir / f"test{i}.png")
            assert result_img.size == (80, 80), f"Image {i}: Expected (80, 80), got {result_img.size}"

    def test_processes_different_image_formats(self, tmp_path):
        """
        Given: PNG and JPG images
        When: downsample
        Then: all images processed
        """
        # Given: PNG and JPG images
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        png_img = Image.new('RGB', (100, 100), color='green')
        png_img.save(img_dir / "test.png")
        jpg_img = Image.new('RGB', (100, 100), color='yellow')
        jpg_img.save(img_dir / "test.jpg")

        # When: downsample
        downsampler = ParallelImageDownsampler()
        result = downsampler.downsample_directory(img_dir, scale=0.5)

        # Then: all images processed (both PNG and JPG)
        assert len(result) == 2, f"Expected 2 images processed, got {len(result)}"
        png_result = Image.open(img_dir / "test.png")
        jpg_result = Image.open(img_dir / "test.jpg")
        assert png_result.size == (50, 50)
        assert jpg_result.size == (50, 50)

    def test_preserves_image_format(self, tmp_path):
        """
        Given: PNG and JPG images
        When: downsample
        Then: PNG stays PNG, JPG stays JPG
        """
        # Given: PNG and JPG images
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        png_img = Image.new('RGB', (100, 100), color='purple')
        png_path = img_dir / "test.png"
        png_img.save(png_path)
        jpg_img = Image.new('RGB', (100, 100), color='orange')
        jpg_path = img_dir / "test.jpg"
        jpg_img.save(jpg_path)

        # When: downsample
        downsampler = ParallelImageDownsampler()
        downsampler.downsample_directory(img_dir, scale=0.7)

        # Then: PNG stays PNG, JPG stays JPG
        png_result = Image.open(png_path)
        jpg_result = Image.open(jpg_path)
        assert png_result.format == 'PNG', f"Expected PNG format, got {png_result.format}"
        assert jpg_result.format == 'JPEG', f"Expected JPEG format, got {jpg_result.format}"

    def test_handles_empty_directory(self, tmp_path):
        """
        Given: empty directory
        When: downsample
        Then: returns empty list, no error
        """
        # Given: empty directory
        img_dir = tmp_path / "empty"
        img_dir.mkdir()

        # When: downsample
        downsampler = ParallelImageDownsampler()
        result = downsampler.downsample_directory(img_dir, scale=0.5)

        # Then: returns empty list, no error
        assert result == [], f"Expected empty list, got {result}"
