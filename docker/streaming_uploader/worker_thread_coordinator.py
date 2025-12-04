import threading
import queue


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
