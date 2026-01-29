"""
Cloud storage operations for GCS.
"""

from pathlib import Path
from google.cloud import storage
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CloudStorage:
    """Handles Google Cloud Storage operations."""

    def upload_and_get_url(self, file_path: Path, bucket_name: str, blob_path: str) -> str:
        """
        Upload file to GCS and return signed URL.

        Args:
            file_path: Local file to upload
            bucket_name: GCS bucket name
            blob_path: Path in bucket

        Returns:
            Signed URL for the uploaded file
        """
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # Upload file (with 60 minute timeout for large files up to 20GB)
        logger.info(f"Uploading {file_path.name} to gs://{bucket_name}/{blob_path}")
        blob.upload_from_filename(str(file_path), timeout=3600)
        logger.info(f"✓ Uploaded {file_path.name} successfully")

        # Generate signed URL (valid for 1 hour)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET"
        )

        return signed_url
