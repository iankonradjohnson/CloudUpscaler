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

    def test_rejects_single_file(self, tmp_path):
        """Edge case: only 1 PNG file (requirements say 2-1000)"""
        from cloud_upscaler import upscale_images

        dir_with_one = tmp_path / "one"
        dir_with_one.mkdir()
        (dir_with_one / "single.png").touch()

        with pytest.raises(ValueError, match="At least 2 PNG files required"):
            upscale_images(
                input_dir=dir_with_one,
                output_dir=Path("/tmp/output")
            )

    def test_upscales_two_files_successfully(self, tmp_path):
        """Happy path: upscale 2 PNG files"""
        from cloud_upscaler import upscale_images

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "page1.png").write_bytes(b"fake png 1")
        (input_dir / "page2.png").write_bytes(b"fake png 2")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = upscale_images(input_dir=input_dir, output_dir=output_dir)

        assert result.success is True

    def test_creates_upscaled_files_in_output_directory(self, tmp_path):
        """Happy path: verify upscaled files are created"""
        from cloud_upscaler import upscale_images

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "page1.png").write_bytes(b"fake png 1")
        (input_dir / "page2.png").write_bytes(b"fake png 2")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        upscale_images(input_dir=input_dir, output_dir=output_dir)

        assert (output_dir / "page1.png").exists()
        assert (output_dir / "page2.png").exists()

    def test_upscaled_files_are_larger_than_input(self, tmp_path):
        """Verify actual upscaling occurred (files should be larger)"""
        from cloud_upscaler import upscale_images

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        small_data = b"small"
        (input_dir / "page1.png").write_bytes(small_data)
        (input_dir / "page2.png").write_bytes(small_data)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        upscale_images(input_dir=input_dir, output_dir=output_dir)

        # Upscaled files should be larger than originals
        assert (output_dir / "page1.png").stat().st_size > len(small_data)
