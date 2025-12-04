from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


class ParallelBatchUploader:

    DEFAULT_MAX_WORKERS = 10

    def __init__(self, storage_client, max_workers: int = DEFAULT_MAX_WORKERS):
        self.storage_client = storage_client
        self.max_workers = max_workers

    def upload_batch(self, batch: list[Path], bucket: str, gcs_prefix: str) -> list[str]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(
                    self.storage_client.upload_and_get_url,
                    img_path,
                    bucket,
                    f"{gcs_prefix}/{img_path.name}"
                )
                for img_path in batch
            ]

            return [future.result() for future in futures]
