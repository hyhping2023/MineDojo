"""Crafting and smelting operations."""

from typing import Any, Dict

from .base import Operation


class CraftOperation(Operation):
    """Craft an item using the env's craft action.

    Issues the craft command via the action space.  For items that require
    a crafting table, navigate to one first before calling this operation.

    Parameters:
        item: Item name to craft (e.g., "planks").
        count: Number to craft (default 1).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "item": {
                "type": "str",
                "description": "Item to craft (e.g. 'planks')",
            },
            "count": {
                "type": "int",
                "description": "Number of items to craft",
                "default": 1,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        item = params.get("item")
        if item is None:
            return False

        count = params.get("count", 1)

        for _ in range(count):
            action = self.env.action_space.no_op()
            if "craft" in action:
                action["craft"] = 1
            obs, _, terminated, _, _ = self.step(action)
            if terminated:
                return False
            self.noop()

        return True


class SmeltOperation(Operation):
    """Smelt an item in a furnace.

    The agent should be near a furnace before calling this operation.

    Parameters:
        item: Item name to smelt (e.g., "iron_ingot").
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "item": {
                "type": "str",
                "description": "Item to smelt (e.g. 'iron_ingot')",
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        item = params.get("item")
        if item is None:
            return False

        action = self.env.action_space.no_op()
        if "smelt" in action:
            action["smelt"] = 1
        self.step(action)
        self.noop()
        return True
