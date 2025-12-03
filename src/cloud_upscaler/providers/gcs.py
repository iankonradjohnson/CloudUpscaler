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
        """Download file from signed URL with streaming"""
        print(f"Downloading from GCS...", flush=True)
        response = requests.get(remote_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    # Print progress every 50MB
                    if downloaded % (50 * 1024 * 1024) < 8192:
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"  Downloaded: {mb_downloaded:.1f}MB / {mb_total:.1f}MB", flush=True)

        print(f"Download complete: {local_path}", flush=True)
