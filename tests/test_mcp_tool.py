"""
Tests for MCP tool wrapper.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path


def test_upscale_images_sync_calls_upscale_images_with_real_providers():
    """MCP tool should initialize real providers and call upscale_images"""
    from cloud_upscaler.mcp_tool import upscale_images_sync

    # Mock environment variables
    with patch.dict('os.environ', {
        'RUNPOD_API_KEY': 'test-runpod-key',
        'RUNPOD_ENDPOINT_ID': 'test-endpoint',
        'RUNPOD_OUTPUT_BUCKET': 'test-output-bucket',
        'RUNPOD_OUTPUT_PATH': 'outputs/results',
        'GCS_BUCKET_NAME': 'test-bucket',
        'GCS_PROJECT_ID': 'test-project'
    }):
        # Mock the provider classes
        with patch('cloud_upscaler.mcp_tool.RunPodComputeProvider') as mock_runpod_class, \
             patch('cloud_upscaler.mcp_tool.GoogleCloudStorageProvider') as mock_gcs_class, \
             patch('cloud_upscaler.mcp_tool.upscale_images') as mock_upscale:

            mock_runpod = Mock()
            mock_gcs = Mock()
            mock_runpod_class.return_value = mock_runpod
            mock_gcs_class.return_value = mock_gcs
            mock_upscale.return_value = Mock(success=True, images_processed=10, error=None)

            # When
            result = upscale_images_sync(
                image_dir="/tmp/input",
                output_dir="/tmp/output"
            )

            # Then
            mock_runpod_class.assert_called_once_with(
                api_key='test-runpod-key',
                endpoint_id='test-endpoint',
                output_bucket='test-output-bucket',
                output_path='outputs/results'
            )
            mock_gcs_class.assert_called_once_with(
                bucket_name='test-bucket',
                project_id='test-project'
            )
            mock_upscale.assert_called_once()
            assert result['success'] is True
            assert result['images_processed'] == 10
