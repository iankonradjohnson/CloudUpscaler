"""
RunPod Serverless compute provider.
"""

import requests


class RunPodComputeProvider:
    """RunPod Serverless API client"""

    def __init__(self, api_key: str, endpoint_id: str):
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"

    def submit_job(self, input_url: str, model_name: str, timeout_seconds: int) -> str:
        """Submit upscaling job to RunPod"""
        response = requests.post(
            f"{self.base_url}/run",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "input": {
                    "input_url": input_url,
                    "model_name": model_name,
                    "timeout_seconds": timeout_seconds
                }
            }
        )
        result = response.json()
        return result["id"]

    def get_job_status(self, job_id: str) -> str:
        """Get job status from RunPod"""
        response = requests.get(
            f"{self.base_url}/status/{job_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        result = response.json()
        return result["status"]

    def get_job_output_url(self, job_id: str) -> str:
        """Get output URL from completed job"""
        pass
