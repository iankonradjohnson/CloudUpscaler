"""
Tests for RunPodComputeProvider.
"""

import pytest
from unittest.mock import Mock, patch


def test_submits_job_to_runpod_api():
    """Should submit job to RunPod /run endpoint with correct payload"""
    from cloud_upscaler.providers.runpod import RunPodComputeProvider

    # Given
    provider = RunPodComputeProvider(
        api_key="test-api-key",
        endpoint_id="test-endpoint",
        output_bucket="test-bucket",
        output_path="output/results"
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
            model_name="net_g_1000000"
        )

        # Then
        assert job_id == "job-123"

        # Verify correct payload was sent (with default params)
        call_args = mock_post.call_args
        assert call_args[1]['json'] == {
            "input": {
                "input_url": "https://storage.googleapis.com/input.zip",
                "output_bucket": "test-bucket",
                "output_path": "output/results",
                "model_name": "net_g_1000000",
                "tile_size": 0,
                "tile_pad": 10,
                "scale": 4,
                "face_enhance": False,
                "fp32": False,
                "gpu_id": "0"
            }
        }


def test_submits_job_with_custom_realesrgan_params():
    """Should accept custom Real-ESRGAN parameters"""
    from cloud_upscaler.providers.runpod import RunPodComputeProvider

    # Given
    provider = RunPodComputeProvider(
        api_key="test-api-key",
        endpoint_id="test-endpoint",
        output_bucket="test-bucket",
        output_path="output/results"
    )

    # Mock the HTTP client
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            "id": "job-456",
            "status": "IN_QUEUE"
        }

        # When - submit with custom params
        realesrgan_params = {
            'tile_size': 512,
            'scale': 2,
            'face_enhance': True,
            'fp32': True,
            'gpu_id': '1'
        }
        job_id = provider.submit_job(
            input_url="https://storage.googleapis.com/input.zip",
            model_name="net_g_1000000",
            realesrgan_params=realesrgan_params
        )

        # Then
        assert job_id == "job-456"

        # Verify custom params were sent
        call_args = mock_post.call_args
        assert call_args[1]['json'] == {
            "input": {
                "input_url": "https://storage.googleapis.com/input.zip",
                "output_bucket": "test-bucket",
                "output_path": "output/results",
                "model_name": "net_g_1000000",
                "tile_size": 512,
                "tile_pad": 10,
                "scale": 2,
                "face_enhance": True,
                "fp32": True,
                "gpu_id": "1"
            }
        }


def test_gets_job_status_from_runpod_api():
    """Should get job status from RunPod /status/{job_id} endpoint"""
    from cloud_upscaler.providers.runpod import RunPodComputeProvider

    # Given
    provider = RunPodComputeProvider(
        api_key="test-api-key",
        endpoint_id="test-endpoint",
        output_bucket="test-bucket",
        output_path="output/results"
    )

    # Mock the HTTP client
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "id": "job-123",
            "status": "COMPLETED"
        }

        # When
        status = provider.get_job_status("job-123")

        # Then
        assert status == "COMPLETED"
        mock_get.assert_called_once()


def test_gets_output_url_from_completed_job():
    """Should get output URL from completed job"""
    from cloud_upscaler.providers.runpod import RunPodComputeProvider

    # Given
    provider = RunPodComputeProvider(
        api_key="test-api-key",
        endpoint_id="test-endpoint",
        output_bucket="test-bucket",
        output_path="output/results"
    )

    # Mock the HTTP client
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "id": "job-123",
            "status": "COMPLETED",
            "output": {
                "output_url": "https://storage.googleapis.com/output.zip"
            }
        }

        # When
        output_url = provider.get_job_output_url("job-123")

        # Then
        assert output_url == "https://storage.googleapis.com/output.zip"
        mock_get.assert_called_once()
