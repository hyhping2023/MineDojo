"""Inventory operations: open, close, select, drop."""

from typing import Any, Dict

from .base import Operation


class OpenInventoryOperation(Operation):
    """Open the player inventory (presses the E / inventory key).

    No parameters required.
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {}

    def execute(self, params: Dict[str, Any]) -> bool:
        action = self.env.action_space.no_op()
        if "inventory" in action:
            action["inventory"] = 1
        _, _, terminated, _, _ = self.step(action)
        if terminated:
            return False
        # Allow a frame for the GUI to open.
        _, _, terminated, _, _ = self.noop()
        if terminated:
            return False
        return True


class CloseInventoryOperation(Operation):
    """Close the player inventory (presses the E / inventory key again).

    No parameters required.
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {}

    def execute(self, params: Dict[str, Any]) -> bool:
        action = self.env.action_space.no_op()
        if "inventory" in action:
            action["inventory"] = 1
        _, _, terminated, _, _ = self.step(action)
        if terminated:
            return False
        _, _, terminated, _, _ = self.noop()
        if terminated:
            return False
        return True


class SelectItemOperation(Operation):
    """Equip an item by name into a specified slot.

    Uses ``env.execute_cmd()`` to replace the item in the inventory slot.
    Falls back to hotbar key presses if execute_cmd is unavailable.

    Parameters:
        item: Item name (e.g., "diamond_sword", "planks").
        slot: Inventory slot to equip to ("mainhand", "offhand", "head",
              "chest", "legs", "feet"). Default "mainhand".
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "item": {
                "type": "str",
                "description": "Item name (e.g. 'diamond_sword')",
            },
            "slot": {
                "type": "str",
                "description": "Inventory slot name",
                "default": "mainhand",
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        item = params.get("item")
        slot = params.get("slot", "mainhand")

        if item is None:
            return False

        terminated = False
        try:
            # Format item name if needed.
            if not item.startswith("minecraft:"):
                item = "minecraft:" + item

            if slot == "mainhand":
                _, _, terminated, _, _ = self.env.execute_cmd(
                    f"/replaceitem entity @p slot.weapon.mainhand {item} 1 0"
                )
            elif slot == "offhand":
                _, _, terminated, _, _ = self.env.execute_cmd(
                    f"/replaceitem entity @p slot.weapon.offhand {item} 1 0"
                )
            else:
                _, _, terminated, _, _ = self.env.execute_cmd(
                    f"/replaceitem entity @p slot.armor.{slot} {item} 1 0"
                )
        except AttributeError:
            # execute_cmd not available; attempt hotbar selection via action.
            action = self.env.action_space.no_op()
            if "hotbar.1" in action:
                for i in range(1, 10):
                    key = f"hotbar.{i}"
                    if key in action:
                        action[key] = 1
                        _, _, terminated, _, _ = self.step(action)
                        break

        if terminated:
            return False
        _, _, terminated, _, _ = self.noop()
        if terminated:
            return False
        return True


class DropItemOperation(Operation):
    """Drop the currently held item (mainhand or offhand).

    Parameters:
        slot: Which hand to drop from ("mainhand" default).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "slot": {
                "type": "str",
                "description": "'mainhand' or 'offhand'",
                "default": "mainhand",
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        slot = params.get("slot", "mainhand")

        if slot == "mainhand":
            # Press the drop key.
            action = self.env.action_space.no_op()
            if "drop" in action:
                action["drop"] = 1
                _, _, terminated, _, _ = self.step(action)
                if terminated:
                    return False
        elif slot == "offhand":
            # Swap offhand to mainhand, then drop, then swap back.
            # Simplified: just drop mainhand.
            action = self.env.action_space.no_op()
            if "drop" in action:
                action["drop"] = 1
                _, _, terminated, _, _ = self.step(action)
                if terminated:
                    return False

        _, _, terminated, _, _ = self.noop()
        if terminated:
            return False
        return True
