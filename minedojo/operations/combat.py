"""Combat operations: attack, spawn-and-attack."""

import math
from typing import Any, Dict

from .base import Operation


class AttackOperation(Operation):
    """Navigate toward a target entity position and attack repeatedly.

    Parameters:
        target_pos: [x, y, z] position of the target entity.
        attack_steps: Number of attack actions to execute (default 20).
        max_nav_steps: Maximum steps to navigate to target (default 300).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "target_pos": {
                "type": "list",
                "description": "[x, y, z] target entity position",
            },
            "attack_steps": {
                "type": "int",
                "description": "Number of attack actions",
                "default": 20,
            },
            "max_nav_steps": {
                "type": "int",
                "description": "Max navigation steps",
                "default": 300,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        target_pos = params.get("target_pos")
        if target_pos is None or len(target_pos) != 3:
            return False

        attack_steps = params.get("attack_steps", 20)
        max_nav_steps = params.get("max_nav_steps", 300)

        # Step 1: Navigate toward target.
        try:
            from minedojo.pathfinding import Navigator
        except ImportError:
            return False

        nav = Navigator(self.env)
        if not nav.navigate_to(
            int(target_pos[0]),
            int(target_pos[1]),
            int(target_pos[2]),
            max_steps=max_nav_steps,
        ):
            return False

        # Step 2: Attack repeatedly.
        for _ in range(attack_steps):
            action = self.env.action_space.no_op()
            if "attack" in action:
                action["attack"] = 1
            obs, _, done, _ = self.step(action)
            if done:
                return False

        return True


class SpawnAttackOperation(Operation):
    """Spawn a mob near the agent, equip a weapon, then attack.

    Parameters:
        mob: Entity name to spawn (e.g., "minecraft:zombie" or "zombie").
        rel_pos: [x, y, z] relative spawn position from agent (default [3, 0, 0]).
        weapon: Item name to equip before attacking (e.g., "diamond_sword").
        attack_steps: Number of attack steps (default 20).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "mob": {
                "type": "str",
                "description": "Entity name to spawn (e.g. 'zombie')",
            },
            "rel_pos": {
                "type": "list",
                "description": "[x, y, z] relative spawn position",
                "default": [3, 0, 0],
            },
            "weapon": {
                "type": "str",
                "description": "Weapon item name",
                "optional": True,
            },
            "attack_steps": {
                "type": "int",
                "description": "Number of attack actions",
                "default": 20,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        mob = params.get("mob")
        if mob is None:
            return False

        rel_pos = params.get("rel_pos", [3, 0, 0])
        weapon = params.get("weapon")
        attack_steps = params.get("attack_steps", 20)

        # Step 1: Spawn the mob.
        if not mob.startswith("minecraft:"):
            mob = "minecraft:" + mob
        self.env.spawn_mobs([mob], [list(rel_pos)])
        self.noop()

        # Step 2: Equip weapon if specified.
        if weapon is not None:
            if not weapon.startswith("minecraft:"):
                weapon = "minecraft:" + weapon
            try:
                self.env.execute_cmd(
                    f"/replaceitem entity @p slot.weapon.mainhand {weapon} 1 0"
                )
            except AttributeError:
                pass
            self.noop()

        # Step 3: Attack.
        for _ in range(attack_steps):
            action = self.env.action_space.no_op()
            if "attack" in action:
                action["attack"] = 1
            obs, _, done, _ = self.step(action)
            if done:
                return True

        return True
