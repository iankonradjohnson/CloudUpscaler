"""
Tests for domain exceptions.

TDD: One test at a time!
"""

import pytest


class TestDomainExceptions:
    """Test domain exception hierarchy"""

    def test_job_not_found_exception_has_job_id(self):
        """
        FIRST TEST: JobNotFoundException carries job_id
        """
        from src.cloud_upscaler.domain.exceptions import JobNotFoundException

        exception = JobNotFoundException("test-job-123")

        assert exception.job_id == "test-job-123"
        assert "test-job-123" in str(exception)
