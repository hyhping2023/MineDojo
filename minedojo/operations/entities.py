"""Entity operations: spawn, interact, mount."""

from typing import Any, Dict

from .base import Operation


class SpawnEntityOperation(Operation):
    """Spawn a Minecraft entity near the agent.

    Parameters:
        entity: Entity type name (e.g., "minecraft:zombie" or "zombie").
        rel_pos: [x, y, z] relative spawn offset from agent (default [3, 0, 0]).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "entity": {
                "type": "str",
                "description": "Entity type (e.g. 'minecraft:zombie')",
            },
            "rel_pos": {
                "type": "list",
                "description": "[x, y, z] relative spawn position",
                "default": [3, 0, 0],
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        entity = params.get("entity")
        if entity is None:
            return False

        if not entity.startswith("minecraft:"):
            entity = "minecraft:" + entity

        rel_pos = params.get("rel_pos", [3, 0, 0])
        self.env.spawn_mobs([entity], [list(rel_pos)])
        self.noop()
        return True


class InteractEntityOperation(Operation):
    """Right-click (use) on a nearby entity.

    Parameters:
        entity_type: Optional entity type for informational purposes.
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "entity_type": {
                "type": "str",
                "description": "Entity type to interact with (informational)",
                "optional": True,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        action = self.env.action_space.no_op()
        if "use" in action:
            action["use"] = 1
        self.step(action)
        self.noop()
        return True


class MountOperation(Operation):
    """Right-click (use) on a ridable entity to mount it.

    Parameters:
        entity_type: Entity type to mount (e.g., "horse", "minecart").
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "entity_type": {
                "type": "str",
                "description": "Ridable entity type (e.g. 'horse')",
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        entity_type = params.get("entity_type")

        action = self.env.action_space.no_op()
        if "use" in action:
            action["use"] = 1
        self.step(action)
        self.noop()
        return True
