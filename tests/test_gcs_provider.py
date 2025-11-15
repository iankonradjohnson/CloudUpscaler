"""
Tests for GoogleCloudStorageProvider.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


def test_uploads_file_to_gcs_and_returns_signed_url():
    """Should upload file to GCS bucket and return signed URL"""
    from cloud_upscaler.providers.gcs import GoogleCloudStorageProvider

    # Mock the GCS client
    with patch('cloud_upscaler.providers.gcs.storage.Client') as mock_client_class:
        mock_client = Mock()
        mock_bucket = Mock()
        mock_blob = Mock()

        mock_client_class.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed-url"

        # Given
        provider = GoogleCloudStorageProvider(
            bucket_name="test-bucket",
            project_id="test-project"
        )

        # When
        signed_url = provider.upload("/tmp/test.zip", "input.zip")

        # Then
        assert signed_url == "https://storage.googleapis.com/signed-url"
        mock_blob.upload_from_filename.assert_called_once_with("/tmp/test.zip")
