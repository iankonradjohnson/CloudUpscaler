"""
Domain value objects.

These are the core business concepts with NO external dependencies.
Rich domain model - objects have BEHAVIOR, not just data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class JobStatus(Enum):
    """Job execution status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class UpscaleConfig:
    """
    Single Responsibility: Represent upscaling configuration
    Reason to change: Upscaling parameters change

    Immutable configuration object with validation.
    """

    model_name: str = "net_g_1000000"
    target_dpi: Optional[int] = None
    tile_size: int = 0
    gpu_count: int = 1
    timeout_seconds: int = 3600

    def __post_init__(self):
        """Validate configuration on creation"""
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if self.timeout_seconds < 60:
            raise ValueError("timeout_seconds must be at least 60")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary"""
        return {
            "model_name": self.model_name,
            "target_dpi": self.target_dpi,
            "tile_size": self.tile_size,
            "gpu_count": self.gpu_count,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class Job:
    """
    Single Responsibility: Represent a compute job with behavior
    Reason to change: Job data model or business rules change

    Rich domain object - knows its own state and transitions.
    """

    job_id: str
    status: JobStatus
    input_url: str
    output_url: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # BEHAVIOR (not just data!)

    def is_terminal(self) -> bool:
        """Check if job is in a terminal state"""
        return self.status in [
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ]

    def is_successful(self) -> bool:
        """Check if job completed successfully"""
        return self.status == JobStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if job failed"""
        return self.status == JobStatus.FAILED

    def can_be_cancelled(self) -> bool:
        """Check if job can be cancelled"""
        return self.status in [JobStatus.PENDING, JobStatus.RUNNING]

    def duration(self) -> Optional[float]:
        """Return job duration in seconds, or None if not completed"""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.submitted_at).total_seconds()

    def mark_completed(self, output_url: str) -> "Job":
        """
        Return new Job instance with completed status (immutable pattern).

        Args:
            output_url: URL to job output

        Returns:
            New Job instance with COMPLETED status
        """
        return Job(
            job_id=self.job_id,
            status=JobStatus.COMPLETED,
            input_url=self.input_url,
            output_url=output_url,
            error_message=None,
            submitted_at=self.submitted_at,
            completed_at=datetime.utcnow(),
            metadata=self.metadata,
        )

    def mark_failed(self, error: str) -> "Job":
        """
        Return new Job instance with failed status (immutable pattern).

        Args:
            error: Error message

        Returns:
            New Job instance with FAILED status
        """
        return Job(
            job_id=self.job_id,
            status=JobStatus.FAILED,
            input_url=self.input_url,
            output_url=None,
            error_message=error,
            submitted_at=self.submitted_at,
            completed_at=datetime.utcnow(),
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class StorageLocation:
    """
    Single Responsibility: Represent a cloud storage location
    Reason to change: Storage location model changes

    Immutable value object representing a file in cloud storage.
    """

    bucket: str
    path: str
    url: Optional[str] = None

    @classmethod
    def from_remote_path(cls, remote_path: str, url: str) -> "StorageLocation":
        """
        Parse remote path into bucket and path components.

        Args:
            remote_path: Path in format "bucket/path/to/file"
            url: Full URL to the file

        Returns:
            StorageLocation instance
        """
        parts = remote_path.split("/", 1)
        bucket = parts[0] if len(parts) > 0 else ""
        path = parts[1] if len(parts) > 1 else remote_path
        return cls(bucket=bucket, path=path, url=url)

    @property
    def full_path(self) -> str:
        """Return full path including bucket"""
        return f"{self.bucket}/{self.path}"

    def __str__(self) -> str:
        return self.url or self.full_path
