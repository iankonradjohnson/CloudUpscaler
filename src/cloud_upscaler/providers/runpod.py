"""
RunPod Serverless compute provider.
"""

import requests


class RunPodComputeProvider:
    """RunPod Serverless API client"""

    def __init__(self, api_key: str, endpoint_id: str, output_bucket: str, output_path: str):
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.output_bucket = output_bucket
        self.output_path = output_path
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"

    def submit_job(self, input_url: str, model_name: str) -> str:
        """Submit upscaling job to RunPod"""
        response = requests.post(
            f"{self.base_url}/run",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "input": {
                    "input_url": input_url,
                    "output_bucket": self.output_bucket,
                    "output_path": self.output_path,
                    "model_name": model_name,
                    "tile_size": 0,
                    "gpu_count": 1
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
        response = requests.get(
            f"{self.base_url}/status/{job_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        result = response.json()

        # Handle RunPod's response wrapping
        # RunPod wraps handler output: {"output": <handler_output>}
        # Our handler returns: {"output": {"output_url": "..."}}
        # So final structure is: {"output": {"output": {"output_url": "..."}}}

        if "output" in result:
            output = result["output"]

            # Check for double-nested output (RunPod wrapping)
            if isinstance(output, dict) and "output" in output:
                inner_output = output["output"]
                if isinstance(inner_output, dict) and "output_url" in inner_output:
                    return inner_output["output_url"]

            # Check for single-nested output
            if isinstance(output, dict) and "output_url" in output:
                return output["output_url"]

            # Direct string output
            if isinstance(output, str):
                return output

        raise KeyError(f"Could not find output_url in response. Response: {result}")
