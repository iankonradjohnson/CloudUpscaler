"""
Tests for upscale_images function.

Starting with edge cases, working toward happy path.
"""

from pathlib import Path
import pytest


class TestUpscaleImages:
    """Test the main upscale_images function"""

    def test_rejects_nonexistent_input_directory(self):
        """Edge case: input_dir doesn't exist"""
        from cloud_upscaler import upscale_images

        nonexistent = Path("/does/not/exist")

        with pytest.raises(ValueError, match="Input directory does not exist"):
            upscale_images(
                input_dir=nonexistent,
                output_dir=Path("/tmp/output")
            )

    def test_rejects_directory_with_no_png_files(self, tmp_path):
        """Edge case: input_dir exists but has no PNG files"""
        from cloud_upscaler import upscale_images

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(ValueError, match="No PNG files found"):
            upscale_images(
                input_dir=empty_dir,
                output_dir=Path("/tmp/output")
            )

    def test_rejects_too_many_files(self, tmp_path):
        """Edge case: more than 1000 PNG files (per requirements)"""
        from cloud_upscaler import upscale_images

        dir_with_many = tmp_path / "many"
        dir_with_many.mkdir()

        # Create 1001 PNG files
        for i in range(1001):
            (dir_with_many / f"image_{i:04d}.png").touch()

        with pytest.raises(ValueError, match="Too many PNG files"):
            upscale_images(
                input_dir=dir_with_many,
                output_dir=Path("/tmp/output")
            )
