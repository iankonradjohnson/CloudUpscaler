from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ParallelBatchUploader:

    DEFAULT_MAX_WORKERS = 10

    def __init__(self, storage_client, max_workers: int = DEFAULT_MAX_WORKERS):
        self.storage_client = storage_client
        self.max_workers = max_workers

    def upload_batch(self, batch: list[Path], bucket: str, gcs_prefix: str) -> list[str]:
        print(f"⬆️  Starting batch upload: {len(batch)} images to gs://{bucket}/{gcs_prefix}", flush=True)
        logger.info(f"Uploading batch of {len(batch)} images with {self.max_workers} parallel workers")
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

            results = [future.result() for future in futures]
            print(f"✅ Batch upload complete: {len(results)} images uploaded to GCS", flush=True)
            logger.info(f"Batch upload complete: {len(results)} images uploaded")
            return results
