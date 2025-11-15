"""
Tests for RunPod Serverless handler.

Using strict TDD with Given-When-Then DSL.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import zipfile
import tempfile


class TestHandlerValidation:
    """Test handler input validation"""

    def test_rejects_job_without_input_url(self):
        """Edge case: job missing input_url should fail clearly"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        job = {
            'input': {
                'output_bucket': 'test-bucket',
                'output_path': 'test/output.zip',
                'model_name': 'net_g_1000000'
            }
        }

        result = handler(job)

        assert result['error'] is not None
        assert 'input_url' in result['error'].lower()

    def test_rejects_job_without_output_bucket(self):
        """Edge case: job missing output_bucket should fail clearly"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        job = {
            'input': {
                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                'output_path': 'test/output.zip',
                'model_name': 'net_g_1000000'
            }
        }

        result = handler(job)

        assert result['error'] is not None
        assert 'output_bucket' in result['error'].lower()

    def test_rejects_job_without_output_path(self):
        """Edge case: job missing output_path should fail clearly"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        job = {
            'input': {
                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                'output_bucket': 'test-bucket',
                'model_name': 'net_g_1000000'
            }
        }

        result = handler(job)

        assert result['error'] is not None
        assert 'output_path' in result['error'].lower()


class TestHandlerDownload:
    """Test handler download functionality"""

    def test_downloads_input_zip_from_url(self, tmp_path):
        """Handler should download ZIP from input_url"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        # Create fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("test.png", b"fake png data")

        # Mock requests.get to return our ZIP
        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        with patch('handler.requests.get', return_value=mock_response) as mock_get:
            # Mock GCS upload/download to avoid real cloud calls
            with patch('handler.storage') as mock_storage:
                mock_client = Mock()
                mock_bucket = Mock()
                mock_blob = Mock()
                mock_blob.generate_signed_url.return_value = "https://fake-signed-url"
                mock_bucket.blob.return_value = mock_blob
                mock_client.bucket.return_value = mock_bucket
                mock_storage.Client.return_value = mock_client

                job = {
                    'input': {
                        'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                        'output_bucket': 'test-bucket',
                        'output_path': 'test/output.zip',
                        'model_name': 'net_g_1000000'
                    }
                }

                result = handler(job)

                # Verify download was called
                mock_get.assert_called_once_with('https://storage.googleapis.com/bucket/input.zip')
