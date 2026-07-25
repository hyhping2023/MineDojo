"""Movement operations: navigate, look-at, strafe."""

import math
from typing import Any, Dict

from .base import Operation

# Minimum yaw change per step to consider as moving toward target.
# This avoids looking-at being a no-op when current yaw is already close.
_YAW_TOLERANCE = 0.5


class NavigateOperation(Operation):
    """Navigate the agent to a target world position using pathfinding.

    Requires the environment to be configured with ``use_voxel=True``.

    Parameters:
        target: [x, y, z] list of world coordinates.
        max_steps: Maximum environment steps before giving up (default 500).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "target": {
                "type": "list",
                "description": "[x, y, z] target world coordinates",
            },
            "max_steps": {
                "type": "int",
                "description": "Maximum steps for navigation",
                "default": 500,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        target = params.get("target")
        if target is None or len(target) != 3:
            return False

        max_steps = params.get("max_steps", 500)

        try:
            from minedojo.pathfinding import Navigator
        except ImportError:
            return False

        nav = Navigator(self.env)
        return nav.navigate_to(
            int(target[0]),
            int(target[1]),
            int(target[2]),
            max_steps=max_steps,
        )


class LookAtOperation(Operation):
    """Rotate the camera to face a target position or a specific yaw/pitch.

    Parameters (choose one):
        target: [x, y, z] world position to look at.
        -- or --
        yaw: Target yaw in degrees (-180 to 180).
        pitch: Target pitch in degrees (-90 to 90).
    """

    _LOOKAT_SPEED = 15.0  # degrees per step

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "target": {
                "type": "list",
                "description": "[x, y, z] world position to look at",
                "optional": True,
            },
            "yaw": {
                "type": "float",
                "description": "Target yaw in degrees",
                "optional": True,
            },
            "pitch": {
                "type": "float",
                "description": "Target pitch in degrees",
                "optional": True,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        target = params.get("target")
        target_yaw = params.get("yaw")
        target_pitch = params.get("pitch")

        # If target position is given, compute yaw from relative position.
        if target is not None and len(target) == 3:
            loc = self.env.prev_obs.get("location_stats", {})
            dx = target[0] - float(loc.get("xpos", 0))
            dz = target[2] - float(loc.get("zpos", 0))
            target_yaw = math.degrees(math.atan2(-dx, dz))
            if target_pitch is None:
                dy = target[1] - float(loc.get("ypos", 0))
                horiz_dist = math.sqrt(dx * dx + dz * dz) or 1.0
                target_pitch = -math.degrees(math.atan2(dy, horiz_dist))

        if target_yaw is None and target_pitch is None:
            return False

        max_steps = 20
        for _ in range(max_steps):
            loc = self.env.prev_obs.get("location_stats", {})
            current_yaw = float(loc.get("yaw", 0))
            current_pitch = float(loc.get("pitch", 0))

            yaw_diff = (target_yaw - current_yaw + 180) % 360 - 180
            pitch_diff = (target_pitch - current_pitch + 90) % 180 - 90

            if abs(yaw_diff) < _YAW_TOLERANCE and abs(pitch_diff) < _YAW_TOLERANCE:
                return True

            action = self.env.action_space.no_op()
            if "camera" in action:
                cam_delta = (
                    max(-1.0, min(1.0, yaw_diff / self._LOOKAT_SPEED)),
                    max(-1.0, min(1.0, pitch_diff / self._LOOKAT_SPEED)),
                )
                action["camera"] = cam_delta

            obs, _, terminated, _, _ = self.step(action)
            if terminated:
                return False

        return True


class StrafeOperation(Operation):
    """Strafe left or right for a given number of steps.

    Parameters:
        direction: "left" or "right".
        steps: Number of environment steps to strafe (default 10).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "direction": {
                "type": "str",
                "description": "'left' or 'right'",
            },
            "steps": {
                "type": "int",
                "description": "Number of steps to strafe",
                "default": 10,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        direction = params.get("direction")
        if direction not in ("left", "right"):
            return False

        steps = params.get("steps", 10)

        for _ in range(steps):
            action = self.env.action_space.no_op()
            if "move" in action:
                action["move"] = direction == "left" and -1 or 1
            obs, _, terminated, _, _ = self.step(action)
            if terminated:
                return False

        return True
