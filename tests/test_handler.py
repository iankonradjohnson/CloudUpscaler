"""
Tests for RunPod Serverless handler.

Using strict TDD with Given-When-Then DSL and real objects with DI.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import zipfile
import sys


@pytest.fixture(autouse=True)
def mock_realesrgan_imports():
    """Automatically mock Real-ESRGAN imports for all tests"""
    sys.modules['torch'] = Mock()
    sys.modules['basicsr'] = Mock()
    sys.modules['basicsr.archs'] = Mock()
    sys.modules['basicsr.archs.rrdbnet_arch'] = Mock()
    sys.modules['realesrgan'] = Mock()
    yield
    # Cleanup
    if 'torch' in sys.modules:
        del sys.modules['torch']
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

    def test_rejects_invalid_tile_size_below_minimum(self, tmp_path):
        """Edge case: tile_size < 32 and not 0 should fail per Real-ESRGAN spec"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: handler with dependencies
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        # When: job submitted with invalid tile_size (not 0, but less than 32)
        job = {
            'input': {
                'input_url': 'https://example.com/input.zip',
                'output_bucket': 'test-bucket',
                'output_path': 'output.zip',
                'tile_size': 16  # Invalid: not 0, but < 32
            }
        }

        # Then: should reject with clear error message
        result = handler.handle(job)
        assert 'error' in result
        assert 'tile_size' in result['error'].lower()
        assert '32' in result['error'] or 'minimum' in result['error'].lower()

    def test_accepts_valid_tile_size_zero(self, tmp_path):
        """Valid case: tile_size=0 (no tiling) should be accepted"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: handler with dependencies
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        # When: job submitted with tile_size=0 (explicit no tiling)
        job = {
            'input': {
                'input_url': 'https://example.com/input.zip',
                'output_bucket': 'test-bucket',
                'output_path': 'output.zip',
                'tile_size': 0  # Valid: no tiling
            }
        }

        # Then: should NOT reject due to tile_size validation
        result = handler.handle(job)
        # It will fail later (404 on URL), but NOT on tile_size validation
        if 'error' in result:
            assert 'tile_size' not in result['error'].lower()

    def test_accepts_valid_tile_size_at_minimum(self, tmp_path):
        """Valid case: tile_size=32 (minimum for tiling) should be accepted"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: handler with dependencies
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        # When: job submitted with tile_size=32 (minimum valid tiling)
        job = {
            'input': {
                'input_url': 'https://example.com/input.zip',
                'output_bucket': 'test-bucket',
                'output_path': 'output.zip',
                'tile_size': 32  # Valid: minimum tile size
            }
        }

        # Then: should NOT reject due to tile_size validation
        result = handler.handle(job)
        # It will fail later (404 on URL), but NOT on tile_size validation
        if 'error' in result:
            assert 'tile_size' not in result['error'].lower()

    def test_rejects_job_without_input_url(self, tmp_path):
        """Edge case: job missing input_url should fail clearly"""
        import sys
        from pathlib import Path

        # Add docker directory to path
        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Real objects with DI
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        # When: Job missing input_url
        job = {
            'input': {
                'output_bucket': 'test-bucket',
                'output_path': 'test/output.zip'
            }
        }

        result = handler.handle(job)

        # Then: Error about missing input_url
        assert 'error' in result
        assert 'input_url' in result['error'].lower()

    def test_rejects_job_without_output_bucket(self):
        """Edge case: job missing output_bucket should fail clearly"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Real objects with DI
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        # When: Job missing output_bucket
        job = {
            'input': {
                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                'output_path': 'test/output.zip'
            }
        }

        result = handler.handle(job)

        # Then: Error about missing output_bucket
        assert 'error' in result
        assert 'output_bucket' in result['error'].lower()

    def test_rejects_job_without_output_path(self):
        """Edge case: job missing output_path should fail clearly"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Real objects with DI
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        # When: Job missing output_path
        job = {
            'input': {
                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                'output_bucket': 'test-bucket'
            }
        }

        result = handler.handle(job)

        # Then: Error about missing output_path
        assert 'error' in result
        assert 'output_path' in result['error'].lower()


class TestHandlerDownload:
    """Test handler download functionality"""

    def test_downloads_input_zip_from_url(self, tmp_path):
        """Handler should download ZIP from input_url"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("test.png", b"fake png data")

        # Mock only external HTTP call
        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response) as mock_get:
            with patch('google.cloud.storage.Client'):
                # Given: Real objects with DI
                handler = Handler(
                    downloader=ImageDownloader(),
                    extractor=ZipExtractor(),
                    upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                    creator=ZipCreator(),
                    storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                )

                job = {
                    'input': {
                        'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                        'output_bucket': 'test-bucket',
                        'output_path': 'test/output.zip'
                    }
                }

                # When: Handle job
                result = handler.handle(job)

                # Then: Download was called
                mock_get.assert_called_once_with('https://storage.googleapis.com/bucket/input.zip')

    def test_extracts_png_files_from_zip(self, tmp_path):
        """Handler should extract PNG files from downloaded ZIP"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP with PNG files
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png 1")
            zf.writestr("image2.png", b"fake png 2")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        extraction_happened = []

        # Track extraction calls
        original_extract = ZipExtractor.extract

        def tracking_extract(self, zip_path, extract_dir):
            extraction_happened.append(True)
            return original_extract(self, zip_path, extract_dir)

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ZipExtractor, 'extract', tracking_extract):
                    # Given: Real objects with DI
                    handler = Handler(
                        downloader=ImageDownloader(),
                        extractor=ZipExtractor(),
                        upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                        creator=ZipCreator(),
                        storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                    )

                    job = {
                        'input': {
                            'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                            'output_bucket': 'test-bucket',
                            'output_path': 'test/output.zip'
                        }
                    }

                    # When: Handle job
                    result = handler.handle(job)

                    # Then: Extraction happened
                    assert len(extraction_happened) > 0


class TestHandlerUpscaling:
    """Test handler upscaling with Real-ESRGAN"""

    def test_upscales_images_with_realesrgan(self, tmp_path):
        """Handler should upscale extracted PNGs with Real-ESRGAN"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png 1")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        upscaling_happened = []

        # Track upscaling calls
        original_upscale = ImageUpscaler.upscale_directory

        def tracking_upscale(self, input_dir, output_dir):
            upscaling_happened.append({'model': self.model_name, 'tile': self.tile_size})
            # Create fake output
            for png in input_dir.glob("*.png"):
                (output_dir / png.name).write_bytes(b"upscaled data")
            return list(output_dir.glob("*.png"))

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', tracking_upscale):
                    # Given: Real objects with DI
                    handler = Handler(
                        downloader=ImageDownloader(),
                        extractor=ZipExtractor(),
                        upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                        creator=ZipCreator(),
                        storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                    )

                    job = {
                        'input': {
                            'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                            'output_bucket': 'test-bucket',
                            'output_path': 'test/output.zip'
                        }
                    }

                    # When: Handle job
                    result = handler.handle(job)

                    # Then: Upscaling happened with correct model
                    assert len(upscaling_happened) > 0
                    assert upscaling_happened[0]['model'] == 'net_g_1000000'


class TestHandlerOutput:
    """Test handler output ZIP and upload"""

    def test_creates_output_zip_from_upscaled_files(self, tmp_path):
        """Handler should create ZIP from upscaled PNG files"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        zip_created = []

        # Track ZIP creation
        original_create = ZipCreator.create

        def tracking_create(self, output_files, zip_path):
            zip_created.append(True)
            return original_create(self, output_files, zip_path)

        def mock_upscale(self, input_dir, output_dir):
            for png in input_dir.glob("*.png"):
                (output_dir / png.name).write_bytes(b"upscaled data")
            return list(output_dir.glob("*.png"))

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', mock_upscale):
                    with patch.object(ZipCreator, 'create', tracking_create):
                        # Given: Real objects with DI
                        handler = Handler(
                            downloader=ImageDownloader(),
                            extractor=ZipExtractor(),
                            upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                            creator=ZipCreator(),
                            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                        )

                        job = {
                            'input': {
                                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                                'output_bucket': 'test-bucket',
                                'output_path': 'test/output.zip'
                            }
                        }

                        # When: Handle job
                        result = handler.handle(job)

                        # Then: ZIP was created
                        assert len(zip_created) > 0

    def test_uploads_to_gcs_and_returns_signed_url(self, tmp_path):
        """Handler should upload output ZIP to GCS and return signed URL"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP
        input_zip = tmp_path / "input.zip"
        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.writestr("image1.png", b"fake png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        # Mock GCS client
        mock_blob = Mock()
        mock_blob.generate_signed_url = Mock(return_value="https://signed-url.gcs/output.zip")
        mock_blob.upload_from_filename = Mock()
        mock_bucket = Mock()
        mock_bucket.blob = Mock(return_value=mock_blob)
        mock_client = Mock()
        mock_client.bucket = Mock(return_value=mock_bucket)

        def mock_upscale(self, input_dir, output_dir):
            for png in input_dir.glob("*.png"):
                (output_dir / png.name).write_bytes(b"upscaled data")
            return list(output_dir.glob("*.png"))

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client', return_value=mock_client):
                with patch.object(ImageUpscaler, 'upscale_directory', mock_upscale):
                    # Given: Real objects with DI
                    handler = Handler(
                        downloader=ImageDownloader(),
                        extractor=ZipExtractor(),
                        upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                        creator=ZipCreator(),
                        storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                    )

                    job = {
                        'input': {
                            'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                            'output_bucket': 'test-bucket',
                            'output_path': 'test/output.zip'
                        }
                    }

                    # When: Handle job
                    result = handler.handle(job)

                    # Then: GCS upload happened and signed URL returned
                    mock_bucket.blob.assert_called()
                    mock_blob.upload_from_filename.assert_called()
                    assert 'output' in result
                    assert 'output_url' in result['output']
                    assert result['output']['output_url'] == "https://signed-url.gcs/output.zip"


class TestHandlerDownsampling:
    """Test handler downsampling functionality"""

    def test_downsamples_images_to_correct_dimensions(self, tmp_path):
        """Handler should downsample upscaled images when downsample_scale < 1.0"""
        import sys
        from pathlib import Path
        from PIL import Image
        import shutil

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP with small test image
        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        # Capture uploaded ZIP by copying it before it's deleted
        captured_zip_path = tmp_path / "captured_output.zip"

        def capture_upload(zip_path):
            shutil.copy(zip_path, captured_zip_path)

        # Mock GCS client
        mock_blob = Mock()
        mock_blob.generate_signed_url = Mock(return_value="https://signed-url.gcs/output.zip")
        mock_blob.upload_from_filename = Mock(side_effect=capture_upload)
        mock_bucket = Mock()
        mock_bucket.blob = Mock(return_value=mock_blob)
        mock_client = Mock()
        mock_client.bucket = Mock(return_value=mock_bucket)

        # Fake upscaler creates 100x100 images
        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (100, 100), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client', return_value=mock_client):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
                    # Given: Real handler with real downsampler
                    handler = Handler(
                        downloader=ImageDownloader(),
                        extractor=ZipExtractor(),
                        upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                        creator=ZipCreator(),
                        storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                    )

                    job = {
                        'input': {
                            'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                            'output_bucket': 'test-bucket',
                            'output_path': 'test/output.zip',
                            'downsample_scale': 0.9  # Downsample to 90%
                        }
                    }

                    # When: Handle job
                    result = handler.handle(job)

                    # Then: Output images should be 90x90 (100 * 0.9)
                    # Extract the captured ZIP and verify dimensions
                    extract_dir = tmp_path / "verify_output"
                    extract_dir.mkdir()
                    with zipfile.ZipFile(captured_zip_path, 'r') as zf:
                        zf.extractall(extract_dir)

                    output_image = Image.open(extract_dir / "test.png")
                    assert output_image.size == (90, 90), f"Expected (90, 90), got {output_image.size}"

    def test_no_downsampling_when_scale_is_one(self, tmp_path):
        """Handler should not downsample when downsample_scale = 1.0"""
        import sys
        from pathlib import Path
        from PIL import Image
        import shutil

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP with small test image
        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        # Capture uploaded ZIP by copying it before it's deleted
        captured_zip_path = tmp_path / "captured_output.zip"

        def capture_upload(zip_path):
            shutil.copy(zip_path, captured_zip_path)

        # Mock GCS client
        mock_blob = Mock()
        mock_blob.generate_signed_url = Mock(return_value="https://signed-url.gcs/output.zip")
        mock_blob.upload_from_filename = Mock(side_effect=capture_upload)
        mock_bucket = Mock()
        mock_bucket.blob = Mock(return_value=mock_blob)
        mock_client = Mock()
        mock_client.bucket = Mock(return_value=mock_bucket)

        # Fake upscaler creates 100x100 images
        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (100, 100), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client', return_value=mock_client):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
                    # Given: Real handler
                    handler = Handler(
                        downloader=ImageDownloader(),
                        extractor=ZipExtractor(),
                        upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                        creator=ZipCreator(),
                        storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                    )

                    job = {
                        'input': {
                            'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                            'output_bucket': 'test-bucket',
                            'output_path': 'test/output.zip',
                            'downsample_scale': 1.0  # No downsampling
                        }
                    }

                    # When: Handle job
                    result = handler.handle(job)

                    # Then: Output images should remain 100x100
                    extract_dir = tmp_path / "verify_output"
                    extract_dir.mkdir()
                    with zipfile.ZipFile(captured_zip_path, 'r') as zf:
                        zf.extractall(extract_dir)

                    output_image = Image.open(extract_dir / "test.png")
                    assert output_image.size == (100, 100), f"Expected (100, 100), got {output_image.size}"

    def test_backward_compatible_when_parameter_omitted(self, tmp_path):
        """Handler should work without downsample_scale parameter (default to 1.0)"""
        import sys
        from pathlib import Path
        from PIL import Image
        import shutil

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Fake input ZIP with small test image
        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        # Capture uploaded ZIP by copying it before it's deleted
        captured_zip_path = tmp_path / "captured_output.zip"

        def capture_upload(zip_path):
            shutil.copy(zip_path, captured_zip_path)

        # Mock GCS client
        mock_blob = Mock()
        mock_blob.generate_signed_url = Mock(return_value="https://signed-url.gcs/output.zip")
        mock_blob.upload_from_filename = Mock(side_effect=capture_upload)
        mock_bucket = Mock()
        mock_bucket.blob = Mock(return_value=mock_blob)
        mock_client = Mock()
        mock_client.bucket = Mock(return_value=mock_bucket)

        # Fake upscaler creates 100x100 images
        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (100, 100), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client', return_value=mock_client):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
                    # Given: Real handler
                    handler = Handler(
                        downloader=ImageDownloader(),
                        extractor=ZipExtractor(),
                        upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
                        creator=ZipCreator(),
                        storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
                    )

                    job = {
                        'input': {
                            'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                            'output_bucket': 'test-bucket',
                            'output_path': 'test/output.zip'
                            # No downsample_scale parameter
                        }
                    }

                    # When: Handle job
                    result = handler.handle(job)

                    # Then: Output images should remain 100x100 (default behavior)
                    extract_dir = tmp_path / "verify_output"
                    extract_dir.mkdir()
                    with zipfile.ZipFile(captured_zip_path, 'r') as zf:
                        zf.extractall(extract_dir)

                    output_image = Image.open(extract_dir / "test.png")
                    assert output_image.size == (100, 100), f"Expected (100, 100), got {output_image.size}"

    def test_rejects_scale_below_minimum(self, tmp_path):
        """Handler should reject downsample_scale < 0.1"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Real handler
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        job = {
            'input': {
                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                'output_bucket': 'test-bucket',
                'output_path': 'test/output.zip',
                'downsample_scale': 0.05  # Invalid: too small
            }
        }

        # When: Handle job
        result = handler.handle(job)

        # Then: Should reject with error
        assert 'error' in result
        assert 'downsample_scale' in result['error'].lower()

    def test_rejects_scale_above_maximum(self, tmp_path):
        """Handler should reject downsample_scale > 1.0"""
        import sys
        from pathlib import Path

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Real handler
        handler = Handler(
            downloader=ImageDownloader(),
            extractor=ZipExtractor(),
            upscaler=ImageUpscaler(model_name='net_g_1000000', tile_size=0),
            creator=ZipCreator(),
            storage=CloudStorage(),
            downsampler=ParallelImageDownsampler()
        )

        job = {
            'input': {
                'input_url': 'https://storage.googleapis.com/bucket/input.zip',
                'output_bucket': 'test-bucket',
                'output_path': 'test/output.zip',
                'downsample_scale': 1.5  # Invalid: upscaling not allowed
            }
        }

        # When: Handle job
        result = handler.handle(job)

        # Then: Should reject with error
        assert 'error' in result
        assert 'downsample_scale' in result['error'].lower()
