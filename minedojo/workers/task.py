"""Task specification and result dataclasses for the video generation system."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class VideoTask:
    """Specifies a video generation task for a worker.

    Attributes:
        task_id: Unique identifier for this task.
        scene_type: Scene config key (e.g. ``"plains"``, ``"cave"``) used to
            match a pre-loaded snapshot and select the right instance.
        operations: Sequence of ``(op_name, params)`` tuples to execute.
        max_steps: Maximum total steps allowed for the operation sequence.
        metadata: Arbitrary key-value metadata for logging / filtering.
    """

    task_id: str
    scene_type: str
    operations: List[Tuple[str, Dict[str, Any]]]
    max_steps: int = 1000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a completed (or failed) video generation task.

    Attributes:
        task_id: Same identifier from the originating :class:`VideoTask`.
        video_path: Absolute path to the generated ``.mp4`` file, or empty
            string on failure.
        success: ``True`` if all operations executed and encoding succeeded.
        frames: Number of POV frames encoded into the video.
        duration_seconds: Wall-clock duration of the task.
        errors: List of error messages (empty on success).
    """

    task_id: str
    video_path: str = ""
    success: bool = False
    frames: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
