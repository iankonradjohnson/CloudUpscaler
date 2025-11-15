"""
Tests for RunPodComputeProvider.
"""

import pytest
from unittest.mock import Mock, patch


def test_submits_job_to_runpod_api():
    """Should submit job to RunPod /run endpoint"""
    from cloud_upscaler.providers.runpod import RunPodComputeProvider

    # Given
    provider = RunPodComputeProvider(
        api_key="test-api-key",
        endpoint_id="test-endpoint"
    )

    # Mock the HTTP client
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            "id": "job-123",
            "status": "IN_QUEUE"
        }

        # When
        job_id = provider.submit_job(
            input_url="https://storage.googleapis.com/input.zip",
            model_name="net_g_1000000",
            timeout_seconds=3600
        )

        # Then
        assert job_id == "job-123"
        mock_post.assert_called_once()
