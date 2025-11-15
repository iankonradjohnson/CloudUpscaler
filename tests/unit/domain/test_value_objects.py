"""
Tests for domain value objects.

Following classicist TDD:
- Start with simplest tests (edge cases)
- Test behavior, not implementation
- Use real objects, not mocks
"""

import pytest
from datetime import datetime


class TestUpscaleConfig:
    """Test UpscaleConfig value object"""

    def test_rejects_empty_model_name(self):
        """
        SIMPLEST TEST: Edge case - empty model name should fail
        (Start with what could go wrong)
        """
        from src.cloud_upscaler.domain.value_objects import UpscaleConfig

        with pytest.raises(ValueError, match="model_name cannot be empty"):
            UpscaleConfig(model_name="")

    def test_rejects_too_short_timeout(self):
        """Edge case: timeout too short"""
        from src.cloud_upscaler.domain.value_objects import UpscaleConfig

        with pytest.raises(ValueError, match="timeout_seconds must be at least 60"):
            UpscaleConfig(timeout_seconds=30)

    def test_creates_valid_config(self):
        """Happy path: valid configuration"""
        from src.cloud_upscaler.domain.value_objects import UpscaleConfig

        config = UpscaleConfig(
            model_name="net_g_1000000",
            timeout_seconds=3600
        )

        assert config.model_name == "net_g_1000000"
        assert config.timeout_seconds == 3600

    def test_config_is_immutable(self):
        """Config should be frozen (immutable)"""
        from src.cloud_upscaler.domain.value_objects import UpscaleConfig

        config = UpscaleConfig(model_name="test_model")

        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            config.model_name = "different_model"

    def test_config_to_dict(self):
        """Config can serialize to dict"""
        from src.cloud_upscaler.domain.value_objects import UpscaleConfig

        config = UpscaleConfig(
            model_name="net_g_1000000",
            target_dpi=600,
            tile_size=512
        )

        result = config.to_dict()

        assert result["model_name"] == "net_g_1000000"
        assert result["target_dpi"] == 600
        assert result["tile_size"] == 512


class TestJobStatus:
    """Test JobStatus enum"""

    def test_has_all_statuses(self):
        """JobStatus enum has all expected values"""
        from src.cloud_upscaler.domain.value_objects import JobStatus

        assert JobStatus.PENDING
        assert JobStatus.RUNNING
        assert JobStatus.COMPLETED
        assert JobStatus.FAILED
        assert JobStatus.CANCELLED


class TestJob:
    """Test Job value object (rich domain model)"""

    def test_job_knows_if_terminal(self):
        """Job can determine if it's in a terminal state"""
        from src.cloud_upscaler.domain.value_objects import Job, JobStatus

        completed_job = Job(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            input_url="http://test.com/input.zip"
        )
        assert completed_job.is_terminal() is True

        failed_job = Job(
            job_id="test-456",
            status=JobStatus.FAILED,
            input_url="http://test.com/input.zip"
        )
        assert failed_job.is_terminal() is True

        running_job = Job(
            job_id="test-789",
            status=JobStatus.RUNNING,
            input_url="http://test.com/input.zip"
        )
        assert running_job.is_terminal() is False

    def test_job_knows_if_successful(self):
        """Job can determine if it completed successfully"""
        from src.cloud_upscaler.domain.value_objects import Job, JobStatus

        job = Job(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            input_url="http://test.com/input.zip"
        )
        assert job.is_successful() is True

        failed_job = Job(
            job_id="test-456",
            status=JobStatus.FAILED,
            input_url="http://test.com/input.zip"
        )
        assert failed_job.is_successful() is False

    def test_job_can_be_marked_completed(self):
        """Job can be marked as completed (returns new instance)"""
        from src.cloud_upscaler.domain.value_objects import Job, JobStatus

        pending_job = Job(
            job_id="test-123",
            status=JobStatus.PENDING,
            input_url="http://test.com/input.zip"
        )

        completed_job = pending_job.mark_completed(
            output_url="http://test.com/output.zip"
        )

        # Returns new instance (immutable pattern)
        assert completed_job.job_id == pending_job.job_id
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.output_url == "http://test.com/output.zip"
        assert completed_job.completed_at is not None

        # Original unchanged
        assert pending_job.status == JobStatus.PENDING

    def test_job_can_calculate_duration(self):
        """Job can calculate its duration"""
        from src.cloud_upscaler.domain.value_objects import Job, JobStatus
        from datetime import datetime, timedelta

        start = datetime(2025, 1, 1, 12, 0, 0)
        end = datetime(2025, 1, 1, 12, 5, 30)  # 5.5 minutes later

        job = Job(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            input_url="http://test.com/input.zip",
            submitted_at=start,
            completed_at=end
        )

        duration = job.duration()
        assert duration == 330.0  # 5.5 minutes = 330 seconds


class TestStorageLocation:
    """Test StorageLocation value object"""

    def test_creates_from_remote_path(self):
        """Can create StorageLocation from remote path string"""
        from src.cloud_upscaler.domain.value_objects import StorageLocation

        location = StorageLocation.from_remote_path(
            "my-bucket/path/to/file.zip",
            "https://storage.googleapis.com/my-bucket/path/to/file.zip"
        )

        assert location.bucket == "my-bucket"
        assert location.path == "path/to/file.zip"
        assert location.url == "https://storage.googleapis.com/my-bucket/path/to/file.zip"

    def test_full_path_property(self):
        """StorageLocation has full_path property"""
        from src.cloud_upscaler.domain.value_objects import StorageLocation

        location = StorageLocation(
            bucket="test-bucket",
            path="folder/file.zip",
            url="http://test.com"
        )

        assert location.full_path == "test-bucket/folder/file.zip"
