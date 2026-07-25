"""Instance pool for coordinating Minecraft instance lifecycle across workers.

Manages metadata about pre-built world snapshots (one per scene type × per_bsz
slots) so that multiple :class:`~minedojo.workers.worker.VideoWorker` processes
can acquire and release instances without race conditions.  Actual
:class:`~minedojo.sim.sim.MineDojoSim` objects are created locally inside
each worker's ``run()`` method — this pool only tracks which snapshots are
in use.
"""

import multiprocessing
from typing import Dict, List, Optional

from minedojo.world_snapshots.config import SCENE_CONFIGS


class InstancePool:
    """Manages a pool of Minecraft world snapshot slots.

    Each slot represents one pre-built world snapshot that can be loaded by
    a worker.  Slots are distributed evenly across scene types.

    Parameters:
        pool_size: Total number of snapshot slots (spread across scene types).
        snapshots_dir: Root directory where world snapshots are stored.
            Each snapshot is expected at ``<snapshots_dir>/<scene_type>/``.
    """

    # Unlike the team-lead sketch we store *relative* snapshot paths and
    # scene_type so the worker can construct the full constructor config.
    # Actual MineDojoSim objects live inside the worker.

    def __init__(
        self,
        pool_size: int = 10,
        snapshots_dir: str = "snapshots",
    ):
        self.pool_size = pool_size
        self.snapshots_dir = snapshots_dir

        # Thread/process-safe primitives
        self._manager = multiprocessing.Manager()
        self._lock = multiprocessing.Lock()

        # Each entry: {scene_type, snapshot_path, instance_id, in_use}
        self._instances: List[Dict] = []

        # Populated by initialize()
        self._initialized = False

    def initialize(self):
        """Create the slot metadata, distributing ``pool_size`` across scene types.

        After this call, slots are available for :meth:`acquire` / :meth:`release`.
        """
        scene_types = list(SCENE_CONFIGS.keys())
        per_scene = max(1, self.pool_size // len(scene_types))

        for scene_type in scene_types:
            for i in range(per_scene):
                snapshot_path = f"{self.snapshots_dir}/{scene_type}"
                self._instances.append({
                    "scene_type": scene_type,
                    "snapshot_path": snapshot_path,
                    "instance_id": len(self._instances),
                    "in_use": False,
                })

        self._initialized = True

    def acquire(self, scene_type: str) -> Optional[Dict]:
        """Acquire an available slot for *scene_type*.

        Returns:
            Slot metadata dict, or ``None`` if no free slot matches.
        """
        if not self._initialized:
            self.initialize()

        with self._lock:
            for inst in self._instances:
                if inst["scene_type"] == scene_type and not inst["in_use"]:
                    inst["in_use"] = True
                    return inst
        return None

    def release(self, instance: Dict):
        """Release a previously acquired slot back to the pool."""
        with self._lock:
            instance["in_use"] = False

    @property
    def available_count(self) -> int:
        """Number of idle slots."""
        return sum(1 for inst in self._instances if not inst["in_use"])

    @property
    def total_count(self) -> int:
        """Total number of slots in the pool."""
        return len(self._instances)
