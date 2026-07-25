"""Block placement operation."""

from typing import Any, Dict

from .base import Operation


class PlaceBlockOperation(Operation):
    """Place a block at a relative position from the agent.

    Uses the env's ``place`` action command to place a block.

    Parameters:
        block_type: Block type to place (e.g., "planks", "cobblestone").
        rel_pos: [x, y, z] relative position from agent (default [0, 0, 1]).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "block_type": {
                "type": "str",
                "description": "Block type name (e.g. 'planks')",
            },
            "rel_pos": {
                "type": "list",
                "description": "[x, y, z] relative position",
                "default": [0, 0, 1],
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        block_type = params.get("block_type")
        if block_type is None:
            return False

        # Ensure the item is in inventory.
        if not block_type.startswith("minecraft:"):
            block_type = "minecraft:" + block_type
        try:
            self.env.execute_cmd(
                f"/replaceitem entity @p slot.weapon.mainhand {block_type} 1 0"
            )
        except AttributeError:
            pass
        self.noop()

        # Execute the place action.
        action = self.env.action_space.no_op()
        if "place" in action:
            action["place"] = 1
        self.step(action)
        self.noop()

        return True
