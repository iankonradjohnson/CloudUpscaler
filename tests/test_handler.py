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




# Test Case List for StreamingImageUploader Integration:
#
# Component: Handler.handle() method modification
# Goal: Replace ZIP creation/upload with StreamingImageUploader
#
# YAGNI-approved tests (6 total):
# [ ] Handler uses StreamingImageUploader to upload images
# [ ] Handler returns list of image URLs in response
# [ ] Handler returns image_count in response
# [ ] Handler returns gcs_prefix in response (without .zip extension)
# [ ] Response does NOT contain 'output_url' key anymore
# [ ] Works with single image


class TestHandlerStreamingUpload:
    """Test handler integration with StreamingImageUploader"""

    def test_handler_uses_streaming_uploader(self, tmp_path):
        """Handler should use StreamingImageUploader to upload images"""
        import sys
        from pathlib import Path
        from PIL import Image
        from unittest.mock import Mock, patch

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        # Given: Input ZIP with test image
        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        # Track if StreamingImageUploader was used
        streaming_upload_called = []

        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (40, 40), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        # Mock StreamingImageUploader
        original_streaming_uploader = None
        try:
            from streaming_uploader import StreamingImageUploader
            original_streaming_uploader = StreamingImageUploader.upload_images_streaming

            def tracking_upload(self, image_paths, bucket, gcs_prefix):
                streaming_upload_called.append({
                    'image_count': len(image_paths),
                    'bucket': bucket,
                    'gcs_prefix': gcs_prefix
                })
                # Return fake URLs
                return [f"https://storage.googleapis.com/{bucket}/{gcs_prefix}/{p.name}" for p in image_paths]

            StreamingImageUploader.upload_images_streaming = tracking_upload
        except ImportError:
            pass

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
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
                            'output_path': 'upscaled/test_output.zip'
                        }
                    }

                    # When: Handle job
                    result = handler.handle(job)

                    # Then: StreamingImageUploader was used
                    assert len(streaming_upload_called) > 0, "StreamingImageUploader should have been called"

        # Restore
        if original_streaming_uploader:
            StreamingImageUploader.upload_images_streaming = original_streaming_uploader

    def test_returns_list_of_image_urls(self, tmp_path):
        """Handler should return list of image URLs in response"""
        import sys
        from pathlib import Path
        from PIL import Image
        from unittest.mock import Mock, patch

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (40, 40), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        try:
            from streaming_uploader import StreamingImageUploader
            original_upload = StreamingImageUploader.upload_images_streaming

            def mock_upload(self, image_paths, bucket, gcs_prefix):
                return [f"https://storage.googleapis.com/{bucket}/{gcs_prefix}/{p.name}" for p in image_paths]

            StreamingImageUploader.upload_images_streaming = mock_upload
        except ImportError:
            pass

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
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
                            'output_path': 'upscaled/test_output.zip'
                        }
                    }

                    result = handler.handle(job)

                    # Then: Response contains image_urls list
                    assert 'output' in result
                    assert 'image_urls' in result['output']
                    assert isinstance(result['output']['image_urls'], list)

        try:
            StreamingImageUploader.upload_images_streaming = original_upload
        except:
            pass

    def test_returns_image_count(self, tmp_path):
        """Handler should return image_count in response"""
        import sys
        from pathlib import Path
        from PIL import Image
        from unittest.mock import Mock, patch

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (40, 40), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        try:
            from streaming_uploader import StreamingImageUploader
            original_upload = StreamingImageUploader.upload_images_streaming

            def mock_upload(self, image_paths, bucket, gcs_prefix):
                return [f"https://storage.googleapis.com/{bucket}/{gcs_prefix}/{p.name}" for p in image_paths]

            StreamingImageUploader.upload_images_streaming = mock_upload
        except ImportError:
            pass

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
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
                            'output_path': 'upscaled/test_output.zip'
                        }
                    }

                    result = handler.handle(job)

                    # Then: Response contains image_count
                    assert 'output' in result
                    assert 'image_count' in result['output']
                    assert result['output']['image_count'] == 1

        try:
            StreamingImageUploader.upload_images_streaming = original_upload
        except:
            pass

    def test_returns_gcs_prefix_without_zip_extension(self, tmp_path):
        """Handler should return gcs_prefix with .zip extension removed"""
        import sys
        from pathlib import Path
        from PIL import Image
        from unittest.mock import Mock, patch

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (40, 40), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        try:
            from streaming_uploader import StreamingImageUploader
            original_upload = StreamingImageUploader.upload_images_streaming

            def mock_upload(self, image_paths, bucket, gcs_prefix):
                return [f"https://storage.googleapis.com/{bucket}/{gcs_prefix}/{p.name}" for p in image_paths]

            StreamingImageUploader.upload_images_streaming = mock_upload
        except ImportError:
            pass

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
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
                            'output_path': 'upscaled/volume_01/pages_output.zip'
                        }
                    }

                    result = handler.handle(job)

                    # Then: gcs_prefix has .zip removed
                    assert 'output' in result
                    assert 'gcs_prefix' in result['output']
                    assert result['output']['gcs_prefix'] == 'upscaled/volume_01/pages_output'
                    assert not result['output']['gcs_prefix'].endswith('.zip')

        try:
            StreamingImageUploader.upload_images_streaming = original_upload
        except:
            pass

    def test_response_does_not_contain_output_url(self, tmp_path):
        """Handler should NOT return output_url key (breaking change)"""
        import sys
        from pathlib import Path
        from PIL import Image
        from unittest.mock import Mock, patch

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "test.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "test.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (40, 40), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        try:
            from streaming_uploader import StreamingImageUploader
            original_upload = StreamingImageUploader.upload_images_streaming

            def mock_upload(self, image_paths, bucket, gcs_prefix):
                return [f"https://storage.googleapis.com/{bucket}/{gcs_prefix}/{p.name}" for p in image_paths]

            StreamingImageUploader.upload_images_streaming = mock_upload
        except ImportError:
            pass

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
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
                            'output_path': 'upscaled/test_output.zip'
                        }
                    }

                    result = handler.handle(job)

                    # Then: output_url key should NOT exist
                    assert 'output' in result
                    assert 'output_url' not in result['output']

        try:
            StreamingImageUploader.upload_images_streaming = original_upload
        except:
            pass

    def test_works_with_single_image(self, tmp_path):
        """Handler should work correctly with just one image"""
        import sys
        from pathlib import Path
        from PIL import Image
        from unittest.mock import Mock, patch

        docker_dir = Path(__file__).parent.parent / 'docker'
        sys.path.insert(0, str(docker_dir))

        from handler import Handler
        from image_downloader import ImageDownloader
        from zip_extractor import ZipExtractor
        from image_upscaler import ImageUpscaler
        from zip_creator import ZipCreator
        from cloud_storage import CloudStorage
        from parallel_image_downsampler import ParallelImageDownsampler

        input_zip = tmp_path / "input.zip"
        test_img = Image.new('RGB', (10, 10), color='red')
        test_img_path = tmp_path / "single.png"
        test_img.save(test_img_path)

        with zipfile.ZipFile(input_zip, 'w') as zf:
            zf.write(test_img_path, "single.png")

        mock_response = Mock()
        mock_response.content = input_zip.read_bytes()
        mock_response.raise_for_status = Mock()

        def fake_upscale(self, input_dir, output_dir):
            for img_file in input_dir.glob("*.png"):
                upscaled_img = Image.new('RGB', (40, 40), color='blue')
                upscaled_img.save(output_dir / img_file.name)
            return list(output_dir.glob("*.png"))

        try:
            from streaming_uploader import StreamingImageUploader
            original_upload = StreamingImageUploader.upload_images_streaming

            def mock_upload(self, image_paths, bucket, gcs_prefix):
                return [f"https://storage.googleapis.com/{bucket}/{gcs_prefix}/{p.name}" for p in image_paths]

            StreamingImageUploader.upload_images_streaming = mock_upload
        except ImportError:
            pass

        with patch('requests.get', return_value=mock_response):
            with patch('google.cloud.storage.Client'):
                with patch.object(ImageUpscaler, 'upscale_directory', fake_upscale):
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
                            'output_path': 'upscaled/test_output.zip'
                        }
                    }

                    result = handler.handle(job)

                    # Then: Should work with 1 image
                    assert 'output' in result
                    assert result['output']['image_count'] == 1
                    assert len(result['output']['image_urls']) == 1

        try:
            StreamingImageUploader.upload_images_streaming = original_upload
        except:
            pass
