from pathlib import Path
import threading
import queue
from concurrent.futures import ThreadPoolExecutor


class BatchCreator:

    def create_batches(self, image_paths: list[Path], batch_size: int) -> list[list[Path]]:
        return [
            image_paths[i:i + batch_size]
            for i in range(0, len(image_paths), batch_size)
        ]


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


class WorkerThreadCoordinator:

    def __init__(self, worker_task):
        self.worker_task = worker_task
        self.task_queue = queue.Queue()
        self.results = []
        self.error = None
        self.worker_thread = None

    def start(self):
        def worker():
            try:
                while True:
                    task = self.task_queue.get()
                    if task is None:
                        break
                    result = self.worker_task(task)
                    if result is not None:
                        self.results.extend(result)
                    self.task_queue.task_done()
            except Exception as e:
                self.error = e

        self.worker_thread = threading.Thread(target=worker)
        self.worker_thread.start()

    def enqueue_task(self, task):
        self.task_queue.put(task)

    def wait_for_completion(self) -> list:
        self.task_queue.put(None)
        self.worker_thread.join()

        if self.error:
            raise self.error

        return self.results


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
        def process_batch(batch):
            return self.batch_uploader.upload_batch(batch, bucket, gcs_prefix)

        coordinator = WorkerThreadCoordinator(worker_task=process_batch)
        coordinator.start()

        batches = self.batch_creator.create_batches(image_paths, self.batch_size)
        for batch in batches:
            coordinator.enqueue_task(batch)

        return coordinator.wait_for_completion()
