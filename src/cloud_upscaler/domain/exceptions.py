"""
Domain exceptions.

Typed exceptions for domain-level errors.
"""


class UpscaleException(Exception):
    """Base exception for upscaling domain"""
    pass


class JobNotFoundException(UpscaleException):
    """Raised when a job cannot be found"""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")
