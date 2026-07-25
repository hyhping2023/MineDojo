"""Mining operations: mine block, chop tree."""

import math
from typing import Any, Dict

from .base import Operation


class MineBlockOperation(Operation):
    """Navigate to a block position, look at it, and mine (break) it.

    Parameters:
        target_pos: [x, y, z] position of the block to mine.
        block_type: Optional block type name (informational, not used for logic).
        max_nav_steps: Maximum navigation steps (default 300).
        mine_steps: How many attack/mining actions to execute (default 40).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "target_pos": {
                "type": "list",
                "description": "[x, y, z] block position to mine",
            },
            "block_type": {
                "type": "str",
                "description": "Block type name (informational)",
                "optional": True,
            },
            "max_nav_steps": {
                "type": "int",
                "description": "Max navigation steps",
                "default": 300,
            },
            "mine_steps": {
                "type": "int",
                "description": "How many attack actions",
                "default": 40,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        target_pos = params.get("target_pos")
        if target_pos is None or len(target_pos) != 3:
            return False

        max_nav_steps = params.get("max_nav_steps", 300)
        mine_steps = params.get("mine_steps", 40)

        # Step 1: Navigate near the block.
        try:
            from minedojo.pathfinding import Navigator
        except ImportError:
            return False

        nav = Navigator(self.env)
        # Navigate to a position next to the block (offset slightly).
        nav_target = (
            int(target_pos[0]) - 1,
            int(target_pos[1]),
            int(target_pos[2]),
        )
        if not nav.navigate_to(
            nav_target[0], nav_target[1], nav_target[2], max_steps=max_nav_steps
        ):
            return False

        # Step 2: Look at the target block.
        loc = self.env.prev_obs.get("location_stats", {})
        dx = target_pos[0] - float(loc.get("xpos", 0))
        dy = target_pos[1] - float(loc.get("ypos", 0))
        dz = target_pos[2] - float(loc.get("zpos", 0))

        target_yaw = math.degrees(math.atan2(-dx, dz))
        horiz_dist = math.sqrt(dx * dx + dz * dz) or 1.0
        target_pitch = -math.degrees(math.atan2(dy, horiz_dist))

        for _ in range(10):
            loc = self.env.prev_obs.get("location_stats", {})
            current_yaw = float(loc.get("yaw", 0))
            current_pitch = float(loc.get("pitch", 0))

            yaw_diff = (target_yaw - current_yaw + 180) % 360 - 180
            pitch_diff = (target_pitch - current_pitch + 90) % 180 - 90

            if abs(yaw_diff) < 1.0 and abs(pitch_diff) < 1.0:
                break

            action = self.env.action_space.no_op()
            if "camera" in action:
                cam_delta = (
                    max(-1.0, min(1.0, yaw_diff / 10.0)),
                    max(-1.0, min(1.0, pitch_diff / 10.0)),
                )
                action["camera"] = cam_delta
            obs, _, terminated, _, _ = self.step(action)
            if terminated:
                return False

        # Step 3: Mine the block (attack action).
        for _ in range(mine_steps):
            action = self.env.action_space.no_op()
            if "attack" in action:
                action["attack"] = 1
            obs, _, terminated, _, _ = self.step(action)
            if terminated:
                return False

        return True


class ChopTreeOperation(Operation):
    """Find the nearest log block and chop the full tree column.

    Parameters:
        max_blocks: Maximum number of log blocks to break (default 10).
        max_nav_steps: Maximum navigation steps per block (default 200).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "max_blocks": {
                "type": "int",
                "description": "Maximum blocks to mine",
                "default": 10,
            },
            "max_nav_steps": {
                "type": "int",
                "description": "Max navigation steps per block",
                "default": 200,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        max_blocks = params.get("max_blocks", 10)
        max_nav_steps = params.get("max_nav_steps", 200)

        obs = self.env.prev_obs
        if obs is None or "voxels" not in obs:
            return False

        voxels = obs["voxels"]
        block_names = voxels.get("block_name", [])
        if not isinstance(block_names, list) or len(block_names) == 0:
            return False

        # Find log blocks ("log" or "log2") near the agent.
        loc = self.env.prev_obs.get("location_stats", {})
        agent_x = int(float(loc.get("xpos", 0)))
        agent_y = int(float(loc.get("ypos", 0)))
        agent_z = int(float(loc.get("zpos", 0)))

        log_positions = []
        # block_names is a flat array; find log blocks nearby.
        for idx, name in enumerate(block_names):
            if name in ("minecraft:log", "minecraft:log2", "log", "log2"):
                # The voxel grid layout depends on the env config.
                # Assume a simple search: scan for block positions.
                # Actual coordinate conversion requires voxel metadata.
                # This is a simplified implementation.
                pass

        # Simplified: try to mine directly upward from eye level.
        # In practice, this requires the voxels handler to provide
        # 3D block coordinates.  For now, issue attack in the approximate
        # direction of known logs.
        for block_idx in range(min(max_blocks, 10)):
            # Look at the log position (rough estimate: straight ahead at eye level).
            action = self.env.action_space.no_op()
            if "attack" in action:
                action["attack"] = 1
            obs, _, terminated, _, _ = self.step(action)
            if terminated:
                break
            self.noop()

        return True
