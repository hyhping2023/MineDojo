"""VideoWorker — a multiprocessing.Process that executes video generation tasks.

Each worker runs in its own process for crash isolation.  It:
1. Pulls a :class:`~minedojo.workers.task.VideoTask` from the task queue.
2. Acquires an instance slot from the :class:`~minedojo.workers.instance_pool.InstancePool`.
3. Creates a :class:`~minedojo.sim.sim.MineDojoSim` from the world snapshot.
4. Randomizes spawn position and inventory.
5. Executes the operation sequence via
   :class:`~minedojo.operations.sequencer.OperationSequencer`.
6. Encodes captured POV frames to H.264 video.
7. Releases the instance slot back to the pool.
8. Pushes a :class:`~minedojo.workers.task.TaskResult` onto the result queue.
"""

import multiprocessing
import random
import time
import traceback
from typing import Optional

import numpy as np

from minedojo.world_snapshots.config import SCENE_CONFIGS, SceneConfig
from minedojo.workers.task import TaskResult


class VideoWorker(multiprocessing.Process):
    """Multiprocessing worker that executes video tasks in its own process.

    Parameters:
        worker_id: Numeric identifier for this worker (used in logs).
        task_queue: Inbound :class:`VideoTask` queue.  A ``None`` sentinel
            signals the worker to exit.
        result_queue: Outbound :class:`TaskResult` queue.
        instance_pool: Shared :class:`InstancePool` for slot coordination.
        snapshots_dir: Root directory where world snapshots are stored.
        output_dir: Directory for video output files.
        image_size: ``(width, height)`` tuple for environment observations.
    """

    def __init__(
        self,
        worker_id: int,
        task_queue: multiprocessing.Queue,
        result_queue: multiprocessing.Queue,
        instance_pool,
        snapshots_dir: str,
        output_dir: str,
        image_size: tuple = (160, 256),
    ):
        super().__init__()
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.instance_pool = instance_pool
        self.snapshots_dir = snapshots_dir
        self.output_dir = output_dir
        self.image_size = image_size

        # These are created inside run() — not at init time, because the
        # objects cannot be pickled / shared across processes.
        self._env = None
        self._sequencer = None
        self._encoder = None

    def run(self):
        """Main loop: pull tasks, execute, encode, report results."""
        from minedojo.sim import MineDojoSim
        from minedojo.sim.inventory import InventoryItem
        from minedojo.operations.sequencer import OperationSequencer
        from minedojo.workers.video_encoder import VideoEncoder

        # MineDojoSim treats image_size as (height, width) — its POV handler
        # sets video_height=image_size[0], video_width=image_size[1]. So the
        # encoder must use width=image_size[1], height=image_size[0] to match
        # the actual frame dimensions (else ffmpeg -s WxH is swapped and the
        # video is distorted).
        self._encoder = VideoEncoder(
            self.output_dir,
            width=self.image_size[1],
            height=self.image_size[0],
        )

        while True:
            task = self.task_queue.get()
            if task is None:
                break  # Sentinel received — shut down

            try:
                result = self._execute_task(task)
                self.result_queue.put(result)
            except Exception as exc:
                self.result_queue.put(TaskResult(
                    task_id=task.task_id,
                    success=False,
                    errors=[traceback.format_exc()],
                ))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_task(self, task) -> TaskResult:
        """Execute a single :class:`VideoTask` and return the result."""
        from minedojo.sim import MineDojoSim
        from minedojo.sim.inventory import InventoryItem
        from minedojo.operations.sequencer import OperationSequencer

        inst = self.instance_pool.acquire(task.scene_type)
        if inst is None:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                errors=[f"No available instance for scene '{task.scene_type}'"],
            )

        env = None
        try:
            # 1. Create environment from snapshot
            scene_cfg = SCENE_CONFIGS.get(task.scene_type)
            env = self._create_env_from_snapshot(inst["snapshot_path"], scene_cfg)
            env.reset()

            # FileWorldGenerator does not always restore the time-of-day and
            # weather from the snapshot's level.dat, so the world can load at
            # night or in a storm. At night Minecraft's lighting is so low that
            # the POV is nearly black and colour information is lost (the
            # three channels end up near-equal). Force midday + clear weather
            # so the POV renders the scene as it was intended.
            try:
                env.set_time(6000)
                env.set_weather("clear")
            except Exception:
                pass  # Non-critical — proceed even if this fails

            # 2. Randomize spawn position within the scene's spawn region
            self._randomize_spawn(env, scene_cfg)

            # 3. Set up inventory from scene config defaults
            self._set_inventory(env, scene_cfg)

            # 4. Execute operation sequence
            start_time = time.time()
            sequencer = OperationSequencer(env)
            seq_result = sequencer.run_sequence(task.operations, task.max_steps)

            # 5. Encode frames to video
            video_path = self._encoder.encode(sequencer.frames, {
                "task_id": task.task_id,
                "scene": task.scene_type,
            })

            duration = time.time() - start_time

            return TaskResult(
                task_id=task.task_id,
                video_path=video_path,
                success=seq_result["success"],
                frames=len(sequencer.frames),
                duration_seconds=duration,
                errors=[seq_result.get("error")] if not seq_result["success"] else [],
            )

        except Exception:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                errors=[traceback.format_exc()],
            )
        finally:
            if env is not None:
                try:
                    env.close()
                except Exception:
                    pass
            self.instance_pool.release(inst)

    def _create_env_from_snapshot(
        self,
        snapshot_path: str,
        scene_cfg: Optional[SceneConfig],
    ):
        """Create a :class:`MineDojoSim` loading the world from a snapshot file."""
        from minedojo.sim import MineDojoSim

        kwargs = {
            "generate_world_type": "from_file",
            "world_file_path": snapshot_path,
            "image_size": self.image_size,
            "sim_name": f"worker_{self.worker_id}_sc_{scene_cfg.name if scene_cfg else 'unknown'}",
            "event_level_control": True,
        }

        # Always load the world from the pre-built snapshot file. The snapshot
        # was built by SnapshotBuilder with the correct world_type/biome and
        # any scene-specific setup (cave room, GUI room, water platform, etc.),
        # so overriding generate_world_type here would discard the pre-built
        # world and regenerate terrain from scratch — which is slow and prone
        # to failures (e.g. "Unable to find spawn biome" for extreme_hills,
        # agent drowning in a random ocean for water).

        return MineDojoSim(**kwargs)

    def _randomize_spawn(self, env, scene_cfg: Optional[SceneConfig]):
        """Teleport agent to a random X/Z within the scene's spawn region.

        Keeps the agent's *current* Y (the snapshot's ground-level spawn) so
        the agent doesn't get placed high in the air and fall to death. Only
        X, Z, and yaw are randomized.
        """
        if scene_cfg is None:
            return

        sr = scene_cfg.spawn_region
        if not sr:
            return

        x = random.uniform(
            sr.get("xmin", -50), sr.get("xmax", 50)
        )
        z = random.uniform(
            sr.get("zmin", -50), sr.get("zmax", 50)
        )
        yaw = random.uniform(0, 360)

        # Preserve the current Y (ground level from the snapshot spawn).
        try:
            loc = env.prev_obs.get("location_stats", {}) if env.prev_obs else {}
            y = float(loc.get("ypos", 64))
        except Exception:
            y = 64.0

        try:
            env.teleport_agent(x, y, z, yaw, 0)
        except Exception:
            pass  # Non-critical — proceed with default spawn

    def _set_inventory(self, env, scene_cfg: Optional[SceneConfig]):
        """Set the agent's inventory from the scene config defaults."""
        from minedojo.sim.inventory import InventoryItem

        if scene_cfg is None or not scene_cfg.default_inventory:
            return

        inventory_list = []
        for idx, item in enumerate(scene_cfg.default_inventory):
            inventory_list.append(
                InventoryItem(
                    slot=idx,
                    name=item["type"],
                    variant=item.get("variant"),
                    quantity=item.get("quantity", 1),
                )
            )

        try:
            env.set_inventory(inventory_list)
        except Exception:
            pass  # Non-critical
