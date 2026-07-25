"""Parallel Video Generation System for MineDojo.

Provides a multiprocessing-based system for generating H.264 videos from
Minecraft gameplay sequences.  Workers acquire Minecraft instances from a
pool, execute operation sequences, encode POV frames to video, and release
instances back to the pool.

Exports:
    VideoTask: Task specification dataclass.
    TaskResult: Task result dataclass.
    InstancePool: Pool of pre-launched Minecraft instance metadata.
    VideoEncoder: H.264 video encoder via ffmpeg subprocess.
    VideoWorker: Multiprocessing worker that executes video tasks.
    TaskScheduler: Scheduler that manages workers and task distribution.
"""

from .task import VideoTask, TaskResult
from .instance_pool import InstancePool
from .video_encoder import VideoEncoder
from .worker import VideoWorker
from .scheduler import TaskScheduler

__all__ = [
    "VideoTask",
    "TaskResult",
    "InstancePool",
    "VideoEncoder",
    "VideoWorker",
    "TaskScheduler",
]
