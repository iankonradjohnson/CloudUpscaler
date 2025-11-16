"""
HTTP and GCS download utility for images.
"""

import requests
from pathlib import Path
from google.cloud import storage


class ImageDownloader:
    """Downloads files from HTTP URLs and GCS."""

    def download(self, url: str, destination: Path) -> Path:
        """
        Download file from URL to destination.
        Supports both HTTP/HTTPS and gs:// URLs.

        Args:
            url: URL to download from (HTTP/HTTPS or gs://)
            destination: Where to save the file

        Returns:
            Path to downloaded file
        """
        if url.startswith('gs://'):
            # GCS download
            return self._download_from_gcs(url, destination)
        else:
            # HTTP download
            response = requests.get(url)
            response.raise_for_status()
            destination.write_bytes(response.content)
            return destination

    def _download_from_gcs(self, gs_url: str, destination: Path) -> Path:
        """
        Download file from GCS.

        Args:
            gs_url: GCS URL (gs://bucket/path/to/file)
            destination: Where to save the file

        Returns:
            Path to downloaded file
        """
        # Parse GCS URL
        # Format: gs://bucket-name/path/to/file
        url_parts = gs_url[5:].split('/', 1)  # Remove 'gs://' and split
        bucket_name = url_parts[0]
        blob_path = url_parts[1] if len(url_parts) > 1 else ''

        # Download from GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.download_to_filename(str(destination))

        return destination
