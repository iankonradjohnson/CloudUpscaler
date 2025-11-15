"""
ZIP file extraction utility.
"""

import zipfile
from pathlib import Path


class ZipExtractor:
    """Extracts files from ZIP archives."""

    def extract(self, zip_path: Path, extract_dir: Path) -> list[Path]:
        """
        Extract ZIP file and return list of PNG files.

        Args:
            zip_path: Path to ZIP file
            extract_dir: Directory to extract to

        Returns:
            List of extracted PNG files
        """
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        png_files = list(extract_dir.glob("*.png"))
        return png_files
