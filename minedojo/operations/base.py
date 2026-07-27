"""Base class and utilities for scripted Minecraft operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class Operation(ABC):
    """Base class for scripted Minecraft operations.

    Each operation encapsulates a specific Minecraft action (navigate, craft,
    attack, mine, etc.) and provides a parameterized execute() method that
    performs the action by stepping the environment.

    Subclasses must implement:
        - get_parameters(): return the parameter space for this operation type.
        - execute(params): perform the operation, return True on success.

    Attributes:
        env: The MineDojoSim (or wrapped) environment instance.
        _step_count: Steps executed since last reset_counter().
        _start_frame: Frame number when execution began.
        _frame_buffer: Optional list that POV frames are appended to after
            each step (used by OperationSequencer to capture video).
    """

    def __init__(self, env, frame_buffer: Optional[List] = None):
        self.env = env
        self._step_count = 0
        self._start_frame = 0
        self._frame_buffer = frame_buffer

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return parameter space description for this operation type.

        Returns:
            A dict describing the expected parameters, e.g.:
            {"target": {"type": "list", "description": "[x, y, z] target position"}}
        """

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> bool:
        """Execute the operation with the given parameters.

        Must call env.step() or step() as part of execution.

        Args:
            params: Dict of parameter values required by this operation.

        Returns:
            True if the operation completed successfully, False otherwise.
        """

    def reset_counter(self):
        """Reset the internal step counter and start frame marker."""
        self._step_count = 0
        self._start_frame = 0

    def step(self, action: Dict[str, Any]) -> Tuple[Any, float, bool, bool, Any]:
        """Execute one environment step and increment the step counter.

        Args:
            action: Action dict compatible with this env's action space.

        Returns:
            (obs, reward, terminated, truncated, info) tuple from env.step().
        """
        obs, reward, terminated, truncated, info = self.env.step(action)
        self._step_count += 1
        # Capture the POV frame for video generation.
        if self._frame_buffer is not None and obs and "pov" in obs:
            self._frame_buffer.append(obs["pov"])
        return obs, reward, terminated, truncated, info

    def noop(self):
        """Execute a single no-op step via the env's action space.

        Returns:
            (obs, reward, terminated, truncated, info) tuple from env.step(no_op()).
        """
        return self.step(self.env.action_space.no_op())
