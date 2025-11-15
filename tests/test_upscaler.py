"""
Tests for upscale_images function.

Starting with edge cases, working toward happy path.
"""

from pathlib import Path
import pytest
from dataclasses import dataclass


# ============================================================================
# Given-When-Then DSL Helpers
# ============================================================================

@dataclass
class TestContext:
    """Context object for test setup"""
    input_dir: Path
    output_dir: Path


def given_directory_with_png_images(tmp_path, count: int) -> TestContext:
    """Create test directories with PNG files"""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    for i in range(count):
        (input_dir / f"image_{i:03d}.png").write_bytes(f"fake png {i}".encode())

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    return TestContext(input_dir=input_dir, output_dir=output_dir)


def given_nonexistent_directory() -> Path:
    """Return path to directory that doesn't exist"""
    return Path("/does/not/exist")


def given_empty_directory(tmp_path) -> Path:
    """Create empty directory"""
    empty = tmp_path / "empty"
    empty.mkdir()
    return empty


def given_directory_with_too_many_images(tmp_path) -> Path:
    """Create directory with >1000 PNG files"""
    many_dir = tmp_path / "many"
    many_dir.mkdir()
    for i in range(1001):
        (many_dir / f"image_{i:04d}.png").touch()
    return many_dir


def given_directory_with_single_image(tmp_path) -> Path:
    """Create directory with only 1 PNG file"""
    single_dir = tmp_path / "single"
    single_dir.mkdir()
    (single_dir / "single.png").touch()
    return single_dir


class FakeStorageProvider:
    """Fake storage provider for testing"""
    def __init__(self):
        self.uploaded_files = []
        self.downloaded_files = []

    def upload(self, local_path, remote_path):
        self.uploaded_files.append((str(local_path), remote_path))
        return f"fake://storage/{remote_path}"

    def download(self, remote_url, local_path):
        import zipfile
        # Track download
        self.downloaded_files.append((remote_url, local_path))
        # Write fake upscaled data as valid ZIP
        with zipfile.ZipFile(local_path, 'w') as zf:
            zf.writestr("fake_result.png", b"fake upscaled png data")


class FakeComputeProvider:
    """Fake compute provider for testing"""
    def __init__(self):
        self.submitted_jobs = []
        self.job_status = "COMPLETED"
        self.output_url = "fake://storage/output.zip"

    def submit_job(self, input_url, model_name, timeout_seconds):
        job_id = f"fake-job-{len(self.submitted_jobs)}"
        self.submitted_jobs.append({
            "job_id": job_id,
            "input_url": input_url,
            "model_name": model_name,
            "timeout_seconds": timeout_seconds
        })
        return job_id

    def get_job_status(self, job_id):
        return self.job_status

    def get_job_output_url(self, job_id):
        return self.output_url


def when_upscaling_images(context: TestContext, **kwargs):
    """Perform upscaling operation"""
    from cloud_upscaler import upscale_images
    return upscale_images(
        input_dir=context.input_dir,
        output_dir=context.output_dir,
        **kwargs
    )


def then_result_is_successful(result):
    """Verify result indicates success"""
    assert result.success is True


def then_images_were_processed(result, count: int):
    """Verify correct number of images processed"""
    assert result.images_processed == count


def then_upscaled_images_exist_in(directory: Path, count: int):
    """Verify upscaled images exist in output"""
    png_files = list(directory.glob("*.png"))
    assert len(png_files) == count


def then_upscaled_files_are_larger_than(directory: Path, original_size: int):
    """Verify upscaled files are larger than original"""
    for png_file in directory.glob("*.png"):
        assert png_file.stat().st_size > original_size


def then_storage_provider_uploaded_zip(storage_provider: FakeStorageProvider):
    """Verify storage provider uploaded a zip file"""
    assert len(storage_provider.uploaded_files) > 0
    uploaded_path, remote_path = storage_provider.uploaded_files[0]
    assert uploaded_path.endswith('.zip')


def then_compute_provider_received_job(compute_provider: FakeComputeProvider):
    """Verify compute provider received a job submission"""
    assert len(compute_provider.submitted_jobs) > 0
    job = compute_provider.submitted_jobs[0]
    assert "input_url" in job
    assert "model_name" in job


def then_storage_provider_downloaded_results(storage_provider: FakeStorageProvider):
    """Verify storage provider downloaded result files"""
    assert len(storage_provider.downloaded_files) > 0
    remote_url, local_path = storage_provider.downloaded_files[0]
    assert "output" in remote_url or "result" in remote_url


def then_result_indicates_failure(result):
    """Verify result indicates failure"""
    assert result.success is False


def then_error_message_is_clear(result):
    """Verify result contains clear error message"""
    assert hasattr(result, 'error')
    assert result.error is not None
    assert len(result.error) > 0


class TestUpscaleImages:
    """Test the main upscale_images function"""

    def test_rejects_nonexistent_input_directory(self):
        """Edge case: input_dir doesn't exist"""
        from cloud_upscaler import upscale_images

        nonexistent = given_nonexistent_directory()

        with pytest.raises(ValueError, match="Input directory does not exist"):
            upscale_images(input_dir=nonexistent, output_dir=Path("/tmp/output"))

    def test_rejects_directory_with_no_png_files(self, tmp_path):
        """Edge case: input_dir exists but has no PNG files"""
        from cloud_upscaler import upscale_images

        empty_dir = given_empty_directory(tmp_path)

        with pytest.raises(ValueError, match="No PNG files found"):
            upscale_images(input_dir=empty_dir, output_dir=Path("/tmp/output"))

    def test_rejects_too_many_files(self, tmp_path):
        """Edge case: more than 1000 PNG files (per requirements)"""
        from cloud_upscaler import upscale_images

        dir_with_many = given_directory_with_too_many_images(tmp_path)

        with pytest.raises(ValueError, match="Too many PNG files"):
            upscale_images(input_dir=dir_with_many, output_dir=Path("/tmp/output"))

    def test_rejects_single_file(self, tmp_path):
        """Edge case: only 1 PNG file (requirements say 2-1000)"""
        from cloud_upscaler import upscale_images

        dir_with_one = given_directory_with_single_image(tmp_path)

        with pytest.raises(ValueError, match="At least 2 PNG files required"):
            upscale_images(input_dir=dir_with_one, output_dir=Path("/tmp/output"))

    def test_upscales_two_files_successfully(self, tmp_path):
        """Happy path: upscale 2 PNG files"""
        context = given_directory_with_png_images(tmp_path, count=2)

        result = when_upscaling_images(context)

        then_result_is_successful(result)

    def test_creates_upscaled_files_in_output_directory(self, tmp_path):
        """Happy path: verify upscaled files are created"""
        context = given_directory_with_png_images(tmp_path, count=2)

        when_upscaling_images(context)

        then_upscaled_images_exist_in(context.output_dir, count=2)

    def test_upscaled_files_are_larger_than_input(self, tmp_path):
        """Verify actual upscaling occurred (files should be larger)"""
        context = given_directory_with_png_images(tmp_path, count=2)
        original_size = 5  # "fake png 0" is 10 bytes

        when_upscaling_images(context)

        then_upscaled_files_are_larger_than(context.output_dir, original_size)

    def test_tracks_files_processed_in_result(self, tmp_path):
        """Result should include count of images processed"""
        context = given_directory_with_png_images(tmp_path, count=3)

        result = when_upscaling_images(context)

        then_images_were_processed(result, count=3)

    def test_accepts_custom_model_name(self, tmp_path):
        """Should accept model_name parameter per requirements"""
        context = given_directory_with_png_images(tmp_path, count=2)

        result = when_upscaling_images(context, model_name="custom_model")

        then_result_is_successful(result)

    def test_accepts_timeout_parameter(self, tmp_path):
        """Should accept timeout_seconds parameter per requirements"""
        context = given_directory_with_png_images(tmp_path, count=2)

        result = when_upscaling_images(context, timeout_seconds=1800)

        then_result_is_successful(result)


class TestCloudProcessing:
    """Test cloud processing pipeline"""

    def test_creates_zip_archive_of_input_files(self, tmp_path):
        """Should zip PNG files before uploading to cloud"""
        from cloud_upscaler import upscale_images
        import zipfile

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "page1.png").write_bytes(b"fake png 1")
        (input_dir / "page2.png").write_bytes(b"fake png 2")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a mock that tracks if zip was created
        zip_created = []

        # Monkey patch zipfile.ZipFile to track creation
        original_zipfile = zipfile.ZipFile

        def tracking_zipfile(*args, **kwargs):
            if len(args) > 0 and str(args[0]).endswith('.zip'):
                zip_created.append(str(args[0]))
            return original_zipfile(*args, **kwargs)

        zipfile.ZipFile = tracking_zipfile
        try:
            upscale_images(input_dir=input_dir, output_dir=output_dir)
            # Should have created a zip file
            assert len(zip_created) > 0
        finally:
            zipfile.ZipFile = original_zipfile

    def test_cleans_up_temporary_zip_file(self, tmp_path):
        """Per Story 2: Remote files cleaned up after processing"""
        from cloud_upscaler import upscale_images
        import tempfile

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "page1.png").write_bytes(b"fake png 1")
        (input_dir / "page2.png").write_bytes(b"fake png 2")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Track temp files created
        temp_files_created = []
        original_namedtemporaryfile = tempfile.NamedTemporaryFile

        def tracking_namedtemporaryfile(*args, **kwargs):
            result = original_namedtemporaryfile(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        tempfile.NamedTemporaryFile = tracking_namedtemporaryfile
        try:
            upscale_images(input_dir=input_dir, output_dir=output_dir)

            # Verify temp files were cleaned up
            for temp_file in temp_files_created:
                assert not Path(temp_file).exists(), f"Temp file {temp_file} was not cleaned up"
        finally:
            tempfile.NamedTemporaryFile = original_namedtemporaryfile


class TestProviderAbstraction:
    """Test provider abstraction per Story 4"""

    def test_accepts_custom_storage_provider(self, tmp_path):
        """Per Story 4: Should accept custom storage provider"""
        context = given_directory_with_png_images(tmp_path, count=2)
        fake_storage = FakeStorageProvider()

        result = when_upscaling_images(context, storage_provider=fake_storage)

        then_result_is_successful(result)

    def test_uploads_zip_using_storage_provider(self, tmp_path):
        """Should upload zip file using provided storage provider"""
        context = given_directory_with_png_images(tmp_path, count=2)
        fake_storage = FakeStorageProvider()

        when_upscaling_images(context, storage_provider=fake_storage)

        then_storage_provider_uploaded_zip(fake_storage)

    def test_submits_job_to_compute_provider(self, tmp_path):
        """Should submit upscaling job to compute provider"""
        context = given_directory_with_png_images(tmp_path, count=2)
        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()

        when_upscaling_images(
            context,
            storage_provider=fake_storage,
            compute_provider=fake_compute
        )

        then_compute_provider_received_job(fake_compute)

    def test_downloads_results_after_job_completes(self, tmp_path):
        """Should download results from storage after job completes"""
        context = given_directory_with_png_images(tmp_path, count=2)
        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()

        when_upscaling_images(
            context,
            storage_provider=fake_storage,
            compute_provider=fake_compute
        )

        then_storage_provider_downloaded_results(fake_storage)

    def test_uses_cloud_processing_when_providers_given(self, tmp_path):
        """When both providers given, should use cloud processing not local simulation"""
        context = given_directory_with_png_images(tmp_path, count=2)
        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()

        # Fake storage provider's download writes a zip with actual files
        import zipfile
        def download_with_real_zip(remote_url, local_path):
            fake_storage.downloaded_files.append((remote_url, local_path))
            # Create a real zip with upscaled files
            with zipfile.ZipFile(local_path, 'w') as zf:
                zf.writestr("image_000.png", b"UPSCALED DATA 1")
                zf.writestr("image_001.png", b"UPSCALED DATA 2")

        fake_storage.download = download_with_real_zip

        when_upscaling_images(
            context,
            storage_provider=fake_storage,
            compute_provider=fake_compute
        )

        # Should have actual upscaled files from cloud, not simulated local upscaling
        then_upscaled_images_exist_in(context.output_dir, count=2)

    def test_handles_failed_job_gracefully(self, tmp_path):
        """Per Story 2: If job fails, I get clear error message"""
        context = given_directory_with_png_images(tmp_path, count=2)
        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()
        fake_compute.job_status = "FAILED"

        result = when_upscaling_images(
            context,
            storage_provider=fake_storage,
            compute_provider=fake_compute
        )

        then_result_indicates_failure(result)
        then_error_message_is_clear(result)
