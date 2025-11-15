"""
HTTP download utility for images.
"""

import requests
from pathlib import Path


class ImageDownloader:
    """Downloads files from HTTP URLs."""

    def download(self, url: str, destination: Path) -> Path:
        """
        Download file from URL to destination.

        Args:
            url: URL to download from
            destination: Where to save the file

        Returns:
            Path to downloaded file
        """
        response = requests.get(url)
        response.raise_for_status()

        destination.write_bytes(response.content)

        return destination
