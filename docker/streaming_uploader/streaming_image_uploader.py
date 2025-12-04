from pathlib import Path
import logging
from .batch_creator import BatchCreator
from .parallel_batch_uploader import ParallelBatchUploader
from .worker_thread_coordinator import WorkerThreadCoordinator

logger = logging.getLogger(__name__)


class StreamingImageUploader:

    def __init__(
        self,
        storage_client,
        batch_creator: BatchCreator,
        batch_uploader: ParallelBatchUploader,
        batch_size: int = 10
    ):
        self.storage_client = storage_client
        self.batch_size = batch_size
        self.batch_creator = batch_creator
        self.batch_uploader = batch_uploader

    @classmethod
    def create_default(cls, storage_client, batch_size: int = 10):
        return cls(
            storage_client=storage_client,
            batch_creator=BatchCreator(),
            batch_uploader=ParallelBatchUploader(storage_client),
            batch_size=batch_size
        )

    def upload_images_streaming(
        self,
        image_paths: list[Path],
        bucket: str,
        gcs_prefix: str
    ) -> list[str]:
        total_images = len(image_paths)
        logger.info(f"Starting streaming upload of {total_images} images to gs://{bucket}/{gcs_prefix}")

        def process_batch(batch):
            return self.batch_uploader.upload_batch(batch, bucket, gcs_prefix)

        coordinator = WorkerThreadCoordinator(worker_task=process_batch)
        coordinator.start()

        batches = self.batch_creator.create_batches(image_paths, self.batch_size)
        total_batches = len(batches)
        logger.info(f"Created {total_batches} batches (batch_size={self.batch_size})")

        for i, batch in enumerate(batches, 1):
            logger.debug(f"Enqueueing batch {i}/{total_batches} ({len(batch)} images)")
            coordinator.enqueue_task(batch)

        logger.info(f"All batches enqueued, waiting for uploads to complete...")
        result = coordinator.wait_for_completion()
        logger.info(f"✓ Upload complete: {len(result)} images uploaded successfully")
        return result
