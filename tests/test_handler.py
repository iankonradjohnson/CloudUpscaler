"""
Tests for RunPod Serverless handler.

Using strict TDD with Given-When-Then DSL.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import zipfile
import tempfile
import sys


@pytest.fixture(autouse=True)
def mock_realesrgan_imports():
    """Automatically mock Real-ESRGAN imports for all tests"""
    sys.modules['basicsr'] = Mock()
    sys.modules['basicsr.archs'] = Mock()
    sys.modules['basicsr.archs.rrdbnet_arch'] = Mock()
    sys.modules['realesrgan'] = Mock()
    yield
    # Cleanup
    if 'basicsr' in sys.modules:
        del sys.modules['basicsr']
    if 'basicsr.archs' in sys.modules:
        del sys.modules['basicsr.archs']
    if 'basicsr.archs.rrdbnet_arch' in sys.modules:
        del sys.modules['basicsr.archs.rrdbnet_arch']
    if 'realesrgan' in sys.modules:
        del sys.modules['realesrgan']


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

    def test_extracts_png_files_from_zip(self, tmp_path):
        """Handler should extract PNG files from downloaded ZIP"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        # Create fake input ZIP with PNG files
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png 1")
            zf.writestr("image2.png", b"fake png 2")

        # Mock requests and GCS
        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        zipfile_calls = []

        # Wrap ZipFile to track calls
        original_zipfile = zipfile.ZipFile

        class TrackingZipFile(original_zipfile):
            def extractall(self, path):
                zipfile_calls.append(('extractall', path))
                return super().extractall(path)

        with patch('handler.requests.get', return_value=mock_response):
            with patch('handler.storage'):
                with patch('handler.zipfile.ZipFile', TrackingZipFile):
                    job = {
                        'input': {
                            'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                            'output_bucket': 'test-bucket',
                            'output_path': 'test/output.zip',
                            'model_name': 'net_g_1000000'
                        }
                    }

                    result = handler(job)

                    # Verify extraction happened
                    assert len([c for c in zipfile_calls if c[0] == 'extractall']) > 0


class TestHandlerUpscaling:
    """Test handler upscaling with Real-ESRGAN"""

    def test_upscales_images_with_realesrgan(self, tmp_path):
        """Handler should upscale extracted PNGs with Real-ESRGAN"""
        import sys
        from pathlib import Path

        # Mock Real-ESRGAN imports before loading handler
        sys.modules['basicsr'] = Mock()
        sys.modules['basicsr.archs'] = Mock()
        sys.modules['basicsr.archs.rrdbnet_arch'] = Mock()
        sys.modules['realesrgan'] = Mock()

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        # Create fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png 1")

        # Mock requests
        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        # Track upscaler creation
        upscaler_created = []

        # Mock ImageUpscaler
        original_init = None

        def mock_upscaler_init(self, model_name="net_g_1000000", tile_size=0):
            upscaler_created.append({'model_name': model_name, 'tile_size': tile_size})
            self.model_name = model_name
            self.tile_size = tile_size

        def mock_upscale_directory(self, input_dir, output_dir):
            # Create fake output files
            for png in input_dir.glob("*.png"):
                (output_dir / png.name).write_bytes(b"upscaled data")
            return list(output_dir.glob("*.png"))

        with patch('handler.requests.get', return_value=mock_response):
            with patch('handler.storage'):
                with patch.object(sys.modules['image_upscaler'].ImageUpscaler, '__init__', mock_upscaler_init):
                    with patch.object(sys.modules['image_upscaler'].ImageUpscaler, 'upscale_directory', mock_upscale_directory):
                        job = {
                            'input': {
                                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                                'output_bucket': 'test-bucket',
                                'output_path': 'test/output.zip',
                                'model_name': 'net_g_1000000'
                            }
                        }

                        result = handler(job)

                        # Verify upscaler was created
                        assert len(upscaler_created) > 0
                        assert upscaler_created[0]['model_name'] == 'net_g_1000000'


class TestHandlerOutput:
    """Test handler output ZIP and upload"""

    def test_creates_output_zip_from_upscaled_files(self, tmp_path):
        """Handler should create ZIP from upscaled PNG files"""
        import sys
        from pathlib import Path

        # Mock Real-ESRGAN imports
        sys.modules['basicsr'] = Mock()
        sys.modules['basicsr.archs'] = Mock()
        sys.modules['basicsr.archs.rrdbnet_arch'] = Mock()
        sys.modules['realesrgan'] = Mock()

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        # Create fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png")

        # Mock everything
        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        zipfile_calls = []

        # Track ZipFile calls
        original_zipfile_init = zipfile.ZipFile.__init__

        def tracking_init(self, file, mode='r', *args, **kwargs):
            zipfile_calls.append(('init', str(file), mode))
            return original_zipfile_init(self, file, mode, *args, **kwargs)

        def mock_upscaler_init(self, model_name="net_g_1000000", tile_size=0):
            self.model_name = model_name
            self.tile_size = tile_size

        def mock_upscale_directory(self, input_dir, output_dir):
            # Create fake output files
            for png in input_dir.glob("*.png"):
                (output_dir / png.name).write_bytes(b"upscaled data")
            return list(output_dir.glob("*.png"))

        with patch('handler.requests.get', return_value=mock_response):
            with patch('handler.storage'):
                with patch.object(zipfile.ZipFile, '__init__', tracking_init):
                    with patch.object(sys.modules['image_upscaler'].ImageUpscaler, '__init__', mock_upscaler_init):
                        with patch.object(sys.modules['image_upscaler'].ImageUpscaler, 'upscale_directory', mock_upscale_directory):
                            job = {
                                'input': {
                                    'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                                    'output_bucket': 'test-bucket',
                                    'output_path': 'test/output.zip',
                                    'model_name': 'net_g_1000000'
                                }
                            }

                            result = handler(job)

                            # Verify output ZIP was created (mode='w')
                            output_zips = [c for c in zipfile_calls if 'output.zip' in c[1] and c[2] == 'w']
                            assert len(output_zips) > 0

    def test_uploads_to_gcs_and_returns_signed_url(self, tmp_path):
        """Handler should upload output ZIP to GCS and return signed URL"""
        import sys
        from pathlib import Path

        # Mock Real-ESRGAN imports
        sys.modules['basicsr'] = Mock()
        sys.modules['basicsr.archs'] = Mock()
        sys.modules['basicsr.archs.rrdbnet_arch'] = Mock()
        sys.modules['realesrgan'] = Mock()

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import handler

        # Create fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png")

        # Mock requests
        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        # Mock GCS
        mock_blob = Mock()
        mock_blob.generate_signed_url = Mock(return_value="https://signed-url.gcs/output.zip")
        mock_bucket = Mock()
        mock_bucket.blob = Mock(return_value=mock_blob)
        mock_client = Mock()
        mock_client.bucket = Mock(return_value=mock_bucket)

        def mock_upscaler_init(self, model_name="net_g_1000000", tile_size=0):
            self.model_name = model_name
            self.tile_size = tile_size

        def mock_upscale_directory(self, input_dir, output_dir):
            # Create fake output files
            for png in input_dir.glob("*.png"):
                (output_dir / png.name).write_bytes(b"upscaled data")
            return list(output_dir.glob("*.png"))

        with patch('handler.requests.get', return_value=mock_response):
            with patch('handler.storage.Client', return_value=mock_client):
                with patch.object(sys.modules['image_upscaler'].ImageUpscaler, '__init__', mock_upscaler_init):
                    with patch.object(sys.modules['image_upscaler'].ImageUpscaler, 'upscale_directory', mock_upscale_directory):
                        job = {
                            'input': {
                                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                                'output_bucket': 'test-bucket',
                                'output_path': 'test/output.zip',
                                'model_name': 'net_g_1000000'
                            }
                        }

                        result = handler(job)

                        # Verify GCS upload happened
                        mock_bucket.blob.assert_called()
                        mock_blob.upload_from_filename.assert_called()
                        # Verify signed URL is returned
                        assert 'output' in result
                        assert 'output_url' in result['output']
                        assert result['output']['output_url'] == "https://signed-url.gcs/output.zip"
