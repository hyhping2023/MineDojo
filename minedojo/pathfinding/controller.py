"""
Path-following controller that converts waypoint paths to Minecraft actions.

Uses a lookahead-based approach: targets a waypoint ahead in the path,
rotates to face it, then moves forward. Handles jumping for upward
transitions and walking off edges for downward transitions.
"""

import math
from copy import deepcopy
from typing import List, Tuple

import numpy as np


class PathFollower:
    """
    Converts a list of waypoint positions into Minecraft action dicts for
    step-by-step following.

    The controller uses a lookahead to target waypoints further ahead in the
    path, which produces smoother movement. When the yaw error is above a
    threshold, the action only contains camera rotation. Once facing the
    target, it adds forward movement (and optionally jump).

    Minecraft coordinate convention:
        - X = east, Y = up, Z = south
        - Yaw: 0 = south, +90 = west, +/-180 = north, -90 = east

    Args:
        env: A ``MineDojoSim`` instance (or compatible wrapper). Used to
             obtain the action space template via ``env.action_space.no_op()``.
        lookahead: Number of waypoints ahead to target.  Default 2.
        yaw_threshold: Degrees of yaw error below which the agent stops
                       rotating and moves forward.  Default 5.0.
        waypoint_radius: Euclidean distance (in blocks) within which a
                         waypoint is considered reached.  Default 0.5.
    """

    def __init__(
        self,
        env,
        lookahead: int = 2,
        yaw_threshold: float = 5.0,
        waypoint_radius: float = 0.5,
    ):
        self.env = env
        self.lookahead = lookahead
        self.yaw_threshold = yaw_threshold
        self.waypoint_radius = waypoint_radius

        # Maximum camera rotation per step, in degrees.  Caps the yaw delta
        # so the agent doesn't snap-rotate unrealistically.
        self.max_rotation_per_step = 30.0

    def get_action(
        self,
        path: List[Tuple[int, int, int]],
        current_pos: Tuple[float, float, float],
        current_yaw: float,
        current_pitch: float,
    ) -> dict:
        """
        Produce an action dict to follow the given path.

        Args:
            path: List of (x, y, z) integer waypoints from A* pathfinder.
            current_pos: Agent's current world position as (x, y, z) floats.
            current_yaw: Agent's current yaw in degrees.
            current_pitch: Agent's current pitch in degrees.

        Returns:
            An action dict compatible with ``MineDojoSim.step()``, containing
            at minimum ``"camera"``, ``"forward"``, and ``"jump"`` keys, with
            all other keys set to their no-op values.
        """
        # Build a no-op action from the environment's action space.
        action = self.env.action_space.no_op()

        if not path:
            return action

        # 1. Find the lookahead waypoint.
        target = self._get_lookahead_waypoint(path, current_pos)

        # 2. Compute desired yaw to face the target.
        #    Minecraft convention: yaw 0 = south, +90 = west, -90 = east.
        #    atan2(dx, -dz) gives angle in radians where 0 = south.
        dx = target[0] - current_pos[0]
        dz = target[2] - current_pos[2]

        if abs(dx) < 1e-6 and abs(dz) < 1e-6:
            # Already at the target waypoint.
            return action

        desired_yaw = math.degrees(math.atan2(-dx, dz))

        # 3. Compute yaw error (shortest rotation).
        yaw_error = self._normalize_angle(desired_yaw - current_yaw)

        # 4. If yaw error is above threshold, issue a rotation-only action.
        if abs(yaw_error) > self.yaw_threshold:
            # Clamp rotation delta per step.
            yaw_delta = np.clip(
                yaw_error, -self.max_rotation_per_step, self.max_rotation_per_step
            )
            # Also adjust pitch slightly toward horizon.
            pitch_delta = -current_pitch * 0.1  # gentle centering
            action["camera"] = np.array(
                [float(pitch_delta), float(yaw_delta)], dtype=np.float32
            )
            return action

        # 5. Facing correctly — decide movement.
        # Small camera adjustment to stay aligned.
        action["camera"] = np.array(
            [-current_pitch * 0.1, float(yaw_error)], dtype=np.float32
        )

        # Forward movement
        action["forward"] = 1

        # Find nearest waypoint and check if the next one requires a jump.
        nearest_idx, _ = self._find_nearest_waypoint(path, current_pos)
        if nearest_idx + 1 < len(path):
            next_wp_idx = nearest_idx + 1
            # Also check one step further for context.
            next_wp = path[next_wp_idx]
            height_diff = next_wp[1] - current_pos[1]
            if height_diff > 0.5:
                action["jump"] = 1

        return action

    def is_waypoint_reached(
        self,
        pos: Tuple[float, float, float],
        waypoint: Tuple[int, int, int],
        radius: float = None,
    ) -> bool:
        """
        Check if the agent is close enough to a waypoint to consider it
        reached.

        Args:
            pos: Current agent position as (x, y, z) floats.
            waypoint: Waypoint as (x, y, z) integers.
            radius: Distance threshold (default: ``self.waypoint_radius``).

        Returns:
            True if the Euclidean distance on the XZ plane is within the
            radius AND the Y difference is within 0.6 (one step height).
        """
        r = radius if radius is not None else self.waypoint_radius
        dx = pos[0] - waypoint[0]
        dy = pos[1] - waypoint[1]
        dz = pos[2] - waypoint[2]
        horiz_dist = math.sqrt(dx * dx + dz * dz)
        return horiz_dist <= r and abs(dy) <= 0.6

    @staticmethod
    def _find_nearest_waypoint(
        path: List[Tuple[int, int, int]],
        current_pos: Tuple[float, float, float],
    ) -> Tuple[int, float]:
        """
        Find the index and squared distance of the nearest waypoint.

        Returns:
            (index, squared_distance)
        """
        nearest_idx = 0
        min_dist = float("inf")
        for i, wp in enumerate(path):
            dx = wp[0] - current_pos[0]
            dy = wp[1] - current_pos[1]
            dz = wp[2] - current_pos[2]
            dist = dx * dx + dy * dy + dz * dz
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i
        return nearest_idx, min_dist

    def _get_lookahead_waypoint(
        self,
        path: List[Tuple[int, int, int]],
        current_pos: Tuple[float, float, float],
    ) -> Tuple[int, int, int]:
        """
        Find the waypoint 'lookahead' steps from the nearest waypoint on the
        path, or the last waypoint if near the end.

        Args:
            path: List of (x, y, z) waypoints.
            current_pos: Agent position as (x, y, z).

        Returns:
            The target waypoint to steer toward.
        """
        nearest_idx, _ = self._find_nearest_waypoint(path, current_pos)
        target_idx = min(nearest_idx + self.lookahead, len(path) - 1)
        return path[target_idx]

    @staticmethod
    def _normalize_angle(angle_deg: float) -> float:
        """Normalize an angle in degrees to the range [-180, 180]."""
        angle_deg = angle_deg % 360.0
        if angle_deg > 180.0:
            angle_deg -= 360.0
        return angle_deg
