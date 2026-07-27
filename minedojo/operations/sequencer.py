"""Operation sequencer for executing sequences of operations and capturing frames."""

from typing import Any, Dict, List, Tuple

import numpy as np

from .registry import OPERATION_REGISTRY


class OperationSequencer:
    """Executes sequences of operations and captures POV frames for video.

    Attributes:
        env: The MineDojoSim (or wrapped) environment instance.
        fps: Frames per second for video capture (informational, default 20).
        frames: Accumulated POV frames from env.prev_obs.
        metadata: Additional metadata about the sequence run.
        ops_executed: Log of operations executed and their success/failure.
    """

    def __init__(self, env, fps: int = 20):
        self.env = env
        self.fps = fps
        self.frames: List[np.ndarray] = []
        self.metadata: Dict[str, Any] = {}
        self.ops_executed: List[Dict] = []

    def run_sequence(
        self,
        operations: List[Tuple[str, Dict[str, Any]]],
        max_steps: int = 1000,
    ) -> Dict[str, Any]:
        """Execute a list of (op_name, params) tuples sequentially.

        Each operation must be registered in OPERATION_REGISTRY.  Operations
        are executed in order.  If any operation returns False, the sequence
        stops early and returns the failure result.

        Args:
            operations: List of (op_name, params) tuples.
            max_steps: (Reserved for future use) Maximum total steps allowed.

        Returns:
            Dict with keys:
                - success (bool): Whether all operations succeeded.
                - ops_executed (list): Log of executed operations.
                - frame_count (int): Number of captured frames.
                - error (str, optional): Error message on failure.
        """
        self.frames = []
        self.ops_executed = []

        # Capture the initial frame (post-reset obs) before any operation.
        self._append_current_frame()

        for op_name, params in operations:
            op_cls = OPERATION_REGISTRY.get(op_name)
            if op_cls is None:
                return {
                    "success": False,
                    "error": f"Unknown operation: {op_name}",
                    "ops_executed": self.ops_executed,
                }

            # Pass our frame buffer so each step() inside the operation
            # appends its POV frame for video generation.
            op = op_cls(self.env, frame_buffer=self.frames)
            success = op.execute(params)
            self.ops_executed.append(
                {"name": op_name, "params": params, "success": success}
            )
            if not success:
                return {
                    "success": False,
                    "ops_executed": self.ops_executed,
                }

        return {
            "success": True,
            "ops_executed": self.ops_executed,
            "frame_count": len(self.frames),
        }

    def _append_current_frame(self) -> None:
        """Append the env's current POV frame to self.frames if available."""
        obs = self.env.prev_obs
        if obs:
            # MineDojoSim's POV handler uses to_string()="rgb"; fall back to
            # "pov" for wrapped/renamed envs.
            frame = obs.get("rgb", obs.get("pov")) if isinstance(obs, dict) else None
            if frame is not None:
                self.frames.append(frame)
