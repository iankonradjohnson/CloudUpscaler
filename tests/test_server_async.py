"""
Tests for async MCP server functions (start_upscale_job, check_upscale_status).

Tests the new async workflow where job submission and status checking are separate operations.
"""

import pytest
from pathlib import Path
import zipfile
import asyncio


# ============================================================================
# Fake Providers (reused from test_upscaler.py pattern)
# ============================================================================

class FakeStorageProvider:
    """Fake storage provider for testing"""
    def __init__(self):
        self.uploaded_files = []
        self.downloaded_files = []

    def upload(self, local_path, remote_path):
        self.uploaded_files.append((str(local_path), remote_path))
        return f"fake://storage/{remote_path}"

    def download(self, remote_url, local_path):
        # Track download
        self.downloaded_files.append((remote_url, local_path))
        # Write fake upscaled data as valid ZIP
        with zipfile.ZipFile(local_path, 'w') as zf:
            zf.writestr("fake_result.jpg", b"fake upscaled jpg data")
            zf.writestr("fake_result2.jpg", b"fake upscaled jpg data 2")


class FakeComputeProvider:
    """Fake compute provider for testing"""
    def __init__(self):
        self.submitted_jobs = []
        self.job_status = "COMPLETED"
        self.output_url = "fake://storage/output.zip"
        self.status_checks = []

    def submit_job(self, input_url, model_name, realesrgan_params=None):
        job_id = f"fake-job-{len(self.submitted_jobs)}"
        self.submitted_jobs.append({
            "job_id": job_id,
            "input_url": input_url,
            "model_name": model_name,
            "realesrgan_params": realesrgan_params
        })
        return job_id

    def get_job_status(self, job_id):
        self.status_checks.append(job_id)
        return self.job_status

    def get_job_output_url(self, job_id):
        return self.output_url


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_dirs(tmp_path):
    """Create test directory structure"""
    book_dir = tmp_path / "book_1"
    book_dir.mkdir()

    input_dir = book_dir / "content_pages"
    input_dir.mkdir()

    # Create fake images
    (input_dir / "page_001.jpg").write_bytes(b"fake image 1")
    (input_dir / "page_002.jpg").write_bytes(b"fake image 2")

    output_dir = book_dir / "upscaled"
    output_dir.mkdir()

    return {
        "book_dir": book_dir,
        "input_dir": input_dir,
        "output_dir": output_dir
    }


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("RUNPOD_API_KEY", "fake-api-key")
    monkeypatch.setenv("RUNPOD_ENDPOINT_ID", "fake-endpoint")
    monkeypatch.setenv("GCS_BUCKET", "fake-bucket")
    monkeypatch.setenv("GCS_PROJECT_ID", "fake-project")


# ============================================================================
# Tests for start_upscale_job
# ============================================================================

class TestStartUpscaleJob:
    """Tests for the start_upscale_job async MCP function"""

    @pytest.mark.asyncio
    async def test_starts_job_and_returns_job_id(self, test_dirs, mock_env, monkeypatch):
        """Test that job is submitted and job ID is returned"""
        from cloud_upscaler.server import start_upscale_job

        # Mock providers
        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()

        def mock_get_storage(*args, **kwargs):
            return fake_storage

        def mock_get_compute(*args, **kwargs):
            return fake_compute

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        # Run start_upscale_job
        arguments = {
            "input_dir": str(test_dirs["input_dir"]),
            "book_dir": str(test_dirs["book_dir"]),
            "gcs_output_path": "upscaled/book_1/output.zip",
            "scale": 4,
            "tile_size": 0,
        }

        result = await start_upscale_job(arguments)

        # Verify result contains job ID
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Job ID: fake-job-0" in result[0].text
        assert "✓ Upscaling job started!" in result[0].text

    @pytest.mark.asyncio
    async def test_saves_job_id_to_file(self, test_dirs, mock_env, monkeypatch):
        """Test that job ID is saved to book_dir/upscaling_job_id.txt"""
        from cloud_upscaler.server import start_upscale_job

        # Mock providers
        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        arguments = {
            "input_dir": str(test_dirs["input_dir"]),
            "book_dir": str(test_dirs["book_dir"]),
            "gcs_output_path": "upscaled/book_1/output.zip",
        }

        await start_upscale_job(arguments)

        # Verify job ID file was created
        job_id_file = test_dirs["book_dir"] / "upscaling_job_id.txt"
        assert job_id_file.exists()
        assert job_id_file.read_text() == "fake-job-0"

    @pytest.mark.asyncio
    async def test_uploads_images_to_gcs(self, test_dirs, mock_env, monkeypatch):
        """Test that images are zipped and uploaded to GCS"""
        from cloud_upscaler.server import start_upscale_job

        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        arguments = {
            "input_dir": str(test_dirs["input_dir"]),
            "book_dir": str(test_dirs["book_dir"]),
            "gcs_output_path": "upscaled/book_1/output.zip",
        }

        await start_upscale_job(arguments)

        # Verify upload happened
        assert len(fake_storage.uploaded_files) == 1
        uploaded_path, remote_path = fake_storage.uploaded_files[0]
        assert remote_path == "input.zip"


# ============================================================================
# Tests for check_upscale_status
# ============================================================================

class TestCheckUpscaleStatus:
    """Tests for the check_upscale_status async MCP function"""

    @pytest.mark.asyncio
    async def test_returns_in_queue_status(self, test_dirs, mock_env, monkeypatch):
        """Test that IN_QUEUE status is properly returned"""
        from cloud_upscaler.server import check_upscale_status

        # Create job ID file
        job_id_file = test_dirs["book_dir"] / "upscaling_job_id.txt"
        job_id_file.write_text("test-job-123")

        # Mock providers
        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()
        fake_compute.job_status = "IN_QUEUE"

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        arguments = {
            "book_dir": str(test_dirs["book_dir"]),
            "output_dir": str(test_dirs["output_dir"]),
        }

        result = await check_upscale_status(arguments)

        assert len(result) == 1
        assert "⏳ Job is queued" in result[0].text
        assert "test-job-123" in result[0].text

    @pytest.mark.asyncio
    async def test_returns_in_progress_status(self, test_dirs, mock_env, monkeypatch):
        """Test that IN_PROGRESS status is properly returned"""
        from cloud_upscaler.server import check_upscale_status

        job_id_file = test_dirs["book_dir"] / "upscaling_job_id.txt"
        job_id_file.write_text("test-job-456")

        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()
        fake_compute.job_status = "IN_PROGRESS"

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        arguments = {
            "book_dir": str(test_dirs["book_dir"]),
            "output_dir": str(test_dirs["output_dir"]),
        }

        result = await check_upscale_status(arguments)

        assert "⚙️ Job is running" in result[0].text

    @pytest.mark.asyncio
    async def test_downloads_results_when_completed(self, test_dirs, mock_env, monkeypatch):
        """Test that results are downloaded when job is COMPLETED"""
        from cloud_upscaler.server import check_upscale_status

        job_id_file = test_dirs["book_dir"] / "upscaling_job_id.txt"
        job_id_file.write_text("test-job-789")

        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()
        fake_compute.job_status = "COMPLETED"

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        arguments = {
            "book_dir": str(test_dirs["book_dir"]),
            "output_dir": str(test_dirs["output_dir"]),
        }

        result = await check_upscale_status(arguments)

        # Verify download happened
        assert len(fake_storage.downloaded_files) == 1

        # Verify success message
        assert "✅ Job COMPLETED!" in result[0].text
        assert "Upscaled images: 2" in result[0].text

    @pytest.mark.asyncio
    async def test_extracts_images_to_output_dir(self, test_dirs, mock_env, monkeypatch):
        """Test that upscaled images are extracted to output directory"""
        from cloud_upscaler.server import check_upscale_status

        job_id_file = test_dirs["book_dir"] / "upscaling_job_id.txt"
        job_id_file.write_text("test-job-extract")

        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()
        fake_compute.job_status = "COMPLETED"

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        arguments = {
            "book_dir": str(test_dirs["book_dir"]),
            "output_dir": str(test_dirs["output_dir"]),
        }

        await check_upscale_status(arguments)

        # Verify images were extracted
        output_files = list(test_dirs["output_dir"].glob("*.jpg"))
        assert len(output_files) == 2
        assert (test_dirs["output_dir"] / "fake_result.jpg").exists()
        assert (test_dirs["output_dir"] / "fake_result2.jpg").exists()

    @pytest.mark.asyncio
    async def test_returns_failed_status(self, test_dirs, mock_env, monkeypatch):
        """Test that FAILED status is properly returned"""
        from cloud_upscaler.server import check_upscale_status

        job_id_file = test_dirs["book_dir"] / "upscaling_job_id.txt"
        job_id_file.write_text("test-job-failed")

        fake_storage = FakeStorageProvider()
        fake_compute = FakeComputeProvider()
        fake_compute.job_status = "FAILED"

        monkeypatch.setattr(
            "cloud_upscaler.server.GoogleCloudStorageProvider",
            lambda *args, **kwargs: fake_storage
        )
        monkeypatch.setattr(
            "cloud_upscaler.server.RunPodComputeProvider",
            lambda *args, **kwargs: fake_compute
        )

        arguments = {
            "book_dir": str(test_dirs["book_dir"]),
            "output_dir": str(test_dirs["output_dir"]),
        }

        result = await check_upscale_status(arguments)

        assert "✗ Job FAILED" in result[0].text

    @pytest.mark.asyncio
    async def test_error_when_job_id_file_missing(self, test_dirs, mock_env):
        """Test that error is returned when job ID file doesn't exist"""
        from cloud_upscaler.server import check_upscale_status

        # Don't create job ID file

        arguments = {
            "book_dir": str(test_dirs["book_dir"]),
            "output_dir": str(test_dirs["output_dir"]),
        }

        result = await check_upscale_status(arguments)

        assert "Error: Job ID file not found" in result[0].text
        assert "Run start_upscale_job first" in result[0].text
