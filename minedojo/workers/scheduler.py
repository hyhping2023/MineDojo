"""Task scheduler for managing worker processes and distributing video tasks."""

import multiprocessing
from typing import List

from .task import VideoTask, TaskResult
from .instance_pool import InstancePool
from .worker import VideoWorker


class TaskScheduler:
    """Manages a pool of :class:`VideoWorker` processes and distributes tasks.

    The scheduler:
    1. Creates an :class:`InstancePool` for slot coordination.
    2. Launches *n_workers* :class:`VideoWorker` processes.
    3. Accepts tasks via :meth:`submit` and :meth:`submit_batch`.
    4. Collects results via :meth:`collect_result` /
       :meth:`collect_results`.
    5. Shuts down workers and releases resources via :meth:`shutdown`.

    Parameters:
        n_workers: Number of worker processes to launch (default 4).
        snapshots_dir: Root directory where world snapshots exist.
        output_dir: Directory where video ``.mp4`` files will be written.
        image_size: ``(width, height)`` for environment observations.
    """

    def __init__(
        self,
        n_workers: int = 4,
        snapshots_dir: str = "snapshots",
        output_dir: str = "output",
        image_size: tuple = (160, 256),
    ):
        self.n_workers = n_workers
        self.snapshots_dir = snapshots_dir
        self.output_dir = output_dir
        self.image_size = image_size

        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()

        self._pool: InstancePool = None
        self._workers: List[VideoWorker] = []
        self._started = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Initialize the instance pool and launch all worker processes."""
        self._pool = InstancePool(
            pool_size=self.n_workers + 2,
            snapshots_dir=self.snapshots_dir,
        )
        self._pool.initialize()

        self._workers = []
        for i in range(self.n_workers):
            w = VideoWorker(
                worker_id=i,
                task_queue=self.task_queue,
                result_queue=self.result_queue,
                instance_pool=self._pool,
                snapshots_dir=self.snapshots_dir,
                output_dir=self.output_dir,
                image_size=self.image_size,
            )
            w.start()
            self._workers.append(w)

        self._started = True

    def submit(self, task: VideoTask):
        """Enqueue a single :class:`VideoTask` for processing.

        :meth:`start` must have been called first.
        """
        self.task_queue.put(task)

    def submit_batch(self, tasks: List[VideoTask]):
        """Enqueue multiple tasks at once."""
        for task in tasks:
            self.submit(task)

    def collect_result(self, timeout: float = None) -> TaskResult:
        """Block until one result is available and return it.

        Parameters:
            timeout: Optional timeout in seconds.  Passed through to
                ``multiprocessing.Queue.get()``.

        Returns:
            The :class:`TaskResult` for the completed task.

        Raises:
            queue.Empty: If *timeout* is set and no result arrives in time.
        """
        return self.result_queue.get(timeout=timeout) if timeout else self.result_queue.get()

    def collect_results(self, count: int) -> List[TaskResult]:
        """Collect exactly *count* results (blocking).

        Assumes *count* tasks have been submitted and no more results
        will arrive beyond those.
        """
        results = []
        for _ in range(count):
            results.append(self.result_queue.get())
        return results

    def shutdown(self):
        """Send sentinels to all workers, join them, and close the pool."""
        # Send shutdown sentinel (None) to each worker
        for _ in self._workers:
            try:
                self.task_queue.put(None)
            except Exception:
                pass

        # Wait for workers to exit
        for w in self._workers:
            try:
                w.join(timeout=30)
                if w.is_alive():
                    w.terminate()
            except Exception:
                pass

        self._workers = []
        self._started = False
