import threading
import queue
import logging

logger = logging.getLogger(__name__)


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
                logger.debug("Worker thread started")
                while True:
                    task = self.task_queue.get()
                    if task is None:
                        logger.debug("Worker thread received stop signal")
                        break
                    logger.debug(f"Processing task: {task}")
                    result = self.worker_task(task)
                    if result is not None:
                        self.results.extend(result)
                    self.task_queue.task_done()
                logger.debug("Worker thread completed successfully")
            except Exception as e:
                logger.error(f"Worker thread encountered error: {e}", exc_info=True)
                self.error = e

        self.worker_thread = threading.Thread(target=worker)
        self.worker_thread.start()
        logger.debug("Worker thread coordinator started")

    def enqueue_task(self, task):
        self.task_queue.put(task)

    def wait_for_completion(self) -> list:
        logger.debug("Sending stop signal to worker thread")
        self.task_queue.put(None)
        logger.debug("Waiting for worker thread to complete")
        self.worker_thread.join()

        if self.error:
            logger.error(f"Worker thread failed with error: {self.error}")
            raise self.error

        logger.debug(f"Worker thread completed successfully with {len(self.results)} results")
        return self.results
