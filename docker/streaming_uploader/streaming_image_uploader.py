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
        print(f"\n{'='*60}", flush=True)
        print(f"📤 STARTING STREAMING UPLOAD", flush=True)
        print(f"   Total images: {total_images}", flush=True)
        print(f"   Batch size: {self.batch_size}", flush=True)
        print(f"   Destination: gs://{bucket}/{gcs_prefix}", flush=True)
        print(f"{'='*60}\n", flush=True)
        logger.info(f"Starting streaming upload of {total_images} images to gs://{bucket}/{gcs_prefix}")

        def process_batch(batch):
            return self.batch_uploader.upload_batch(batch, bucket, gcs_prefix)

        coordinator = WorkerThreadCoordinator(worker_task=process_batch)
        coordinator.start()

        batches = self.batch_creator.create_batches(image_paths, self.batch_size)
        total_batches = len(batches)
        print(f"📦 Created {total_batches} batches of ~{self.batch_size} images each", flush=True)
        logger.info(f"Created {total_batches} batches (batch_size={self.batch_size})")

        for i, batch in enumerate(batches, 1):
            print(f"🔄 Enqueueing batch {i}/{total_batches} ({len(batch)} images)", flush=True)
            logger.info(f"Enqueueing batch {i}/{total_batches} ({len(batch)} images)")
            coordinator.enqueue_task(batch)

        print(f"\n⏳ All batches enqueued, waiting for uploads to complete...\n", flush=True)
        logger.info(f"All batches enqueued, waiting for uploads to complete...")
        result = coordinator.wait_for_completion()
        print(f"\n{'='*60}", flush=True)
        print(f"✅ UPLOAD COMPLETE: {len(result)} images uploaded successfully", flush=True)
        print(f"{'='*60}\n", flush=True)
        logger.info(f"✓ Upload complete: {len(result)} images uploaded successfully")
        return result
