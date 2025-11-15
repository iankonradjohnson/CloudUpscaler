"""
Google Cloud Storage provider.
"""

from google.cloud import storage
from datetime import timedelta
from pathlib import Path
import requests


class GoogleCloudStorageProvider:
    """Google Cloud Storage client"""

    def __init__(self, bucket_name: str, project_id: str = None):
        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    def upload(self, local_path: str, remote_path: str) -> str:
        """Upload file to GCS and return signed URL"""
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(local_path)

        # Generate signed URL valid for 1 hour
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET"
        )
        return signed_url

    def download(self, remote_url: str, local_path: str):
        """Download file from signed URL"""
        response = requests.get(remote_url)
        Path(local_path).write_bytes(response.content)
