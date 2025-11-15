"""
ZIP file creation utility.
"""

import zipfile
from pathlib import Path


class ZipCreator:
    """Creates ZIP archives from files."""

    def create(self, output_files: list[Path], zip_path: Path) -> Path:
        """
        Create ZIP file from list of files.

        Args:
            output_files: List of files to include
            zip_path: Path where ZIP should be created

        Returns:
            Path to created ZIP file
        """
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for file in output_files:
                zf.write(file, file.name)

        return zip_path
