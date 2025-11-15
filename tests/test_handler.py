"""
Tests for RunPod Serverless handler.

Using strict TDD with Given-When-Then DSL.
"""

import pytest
from pathlib import Path


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
