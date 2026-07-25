"""
High-level navigator that ties VoxelMap, AStarPathfinder, and PathFollower
together for goal-directed movement in Minecraft.
"""

import math
from typing import Optional, Tuple

from .voxel_map import VoxelMap
from .astar import AStarPathfinder
from .controller import PathFollower


class Navigator:
    """
    High-level navigation interface combining mapping, pathfinding, and
    closed-loop control.

    Usage::

        env = MineDojoSim(use_voxel=True, voxel_size={...})
        env.reset()
        nav = Navigator(env)
        success = nav.navigate_to(10, 64, 20)

    The navigator continuously updates its internal :class:`VoxelMap` from
    voxel observations, replans paths as new map data becomes available, and
    issues actions via a :class:`PathFollower`.

    Args:
        env: A ``MineDojoSim`` instance configured with ``use_voxel=True``
             and appropriate ``voxel_size``.
        voxel_map: Optional pre-configured :class:`VoxelMap`.  If not given,
                   one is created with default voxel bounds.
        lookahead: Number of waypoints ahead for the :class:`PathFollower`.
        yaw_threshold: Yaw error threshold in degrees for the
                       :class:`PathFollower`.
    """

    def __init__(
        self,
        env,
        voxel_map: Optional[VoxelMap] = None,
        lookahead: int = 2,
        yaw_threshold: float = 5.0,
        replan_interval: int = 5,
    ):
        self.env = env
        self.voxel_map = voxel_map or VoxelMap()
        self.pathfinder = AStarPathfinder(self.voxel_map)
        self.follower = PathFollower(
            env, lookahead=lookahead, yaw_threshold=yaw_threshold
        )
        self.replan_interval = replan_interval  # Replan every N steps

    def navigate_to(
        self,
        target_x: int,
        target_y: int,
        target_z: int,
        max_steps: int = 500,
    ) -> bool:
        """
        Navigate the agent to the target world position.

        Args:
            target_x: Target world X coordinate (integer).
            target_y: Target world Y coordinate (integer).
            target_z: Target world Z coordinate (integer).
            max_steps: Maximum number of ``env.step()`` calls before giving
                       up.  Default 500.

        Returns:
            ``True`` if the target was reached within ``max_steps``, or
            ``False`` if the step limit was exceeded or no path could be
            found.
        """
        target = (target_x, target_y, target_z)

        for step in range(max_steps):
            # 1. Read current observation.
            obs = self.env.prev_obs
            if obs is None:
                raise RuntimeError(
                    "Navigator requires env to have been reset() before navigate_to()"
                )

            # 2. Update the voxel map with the latest observation.
            self.voxel_map.update(obs)

            # 3. Get current position and orientation.
            pos, yaw, pitch = self._get_pose(obs)
            current_block = (int(math.floor(pos[0])), int(math.floor(pos[1])), int(math.floor(pos[2])))

            # 4. Check if we've reached the target.
            if self._is_near_target(pos, target):
                return True

            # 5. Plan a path from the current position.
            #    Replan every N steps or if we don't have a path yet.
            if step % self.replan_interval == 0 or step == 0:
                path = self.pathfinder.find_path(current_block, target)

            if path is None or len(path) == 0:
                # No path found — try updating map and replanning next step.
                # If we can't find a path at all, it may help to do a no-op
                # step to get fresh observations.
                self.env.step(self.env.action_space.no_op())
                continue

            # Remove waypoints that have already been reached.
            path = self._trim_reached_waypoints(path, pos)

            if len(path) == 0:
                # Should not happen after trim, but if so, we're at target.
                continue

            # 6. Get the next action.
            action = self.follower.get_action(path, pos, yaw, pitch)

            # 7. Execute the action.
            self.env.step(action)

        # Max steps exceeded.
        return False

    def _get_pose(
        self, obs: dict
    ) -> Tuple[Tuple[float, float, float], float, float]:
        """
        Extract agent position and orientation from an observation dict.

        Returns:
            ((x, y, z), yaw, pitch) — yaw and pitch in degrees.
        """
        location = obs.get("location_stats", {})
        # Actual observation format: xpos, ypos, zpos, yaw, pitch (individual float32 scalars)
        pos = (
            float(location.get("xpos", 0.0)),
            float(location.get("ypos", 0.0)),
            float(location.get("zpos", 0.0)),
        )
        yaw = float(location.get("yaw", 0.0))
        pitch = float(location.get("pitch", 0.0))

        return pos, yaw, pitch

    @staticmethod
    def _is_near_target(
        pos: Tuple[float, float, float],
        target: Tuple[int, int, int],
        horiz_threshold: float = 0.5,
        vert_threshold: float = 0.6,
    ) -> bool:
        """Check if the agent is close enough to the target block."""
        dx = pos[0] - target[0]
        dy = pos[1] - target[1]
        dz = pos[2] - target[2]
        return math.sqrt(dx * dx + dz * dz) < horiz_threshold and abs(dy) < vert_threshold

    def _trim_reached_waypoints(
        self,
        path: list,
        pos: Tuple[float, float, float],
    ) -> list:
        """Remove waypoints the agent has already reached."""
        while len(path) > 1 and self.follower.is_waypoint_reached(pos, path[0]):
            path.pop(0)
        return path
