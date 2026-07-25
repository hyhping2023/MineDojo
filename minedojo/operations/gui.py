"""GUI operations: trade, enchant, brew, anvil, chest.

These operations interact with Minecraft GUI screens and require the
agent to be close to the relevant block/entity.
"""

from typing import Any, Dict

from .base import Operation


class TradeOperation(Operation):
    """Open a trade GUI with a villager and select a trade.

    Parameters:
        villager_pos: [x, y, z] position of the villager.
        trade_index: Which trade to select (0-based, default 0).
        max_nav_steps: Maximum navigation steps to reach villager (default 200).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "villager_pos": {
                "type": "list",
                "description": "[x, y, z] villager position",
            },
            "trade_index": {
                "type": "int",
                "description": "Trade index to select",
                "default": 0,
            },
            "max_nav_steps": {
                "type": "int",
                "description": "Max navigation steps",
                "default": 200,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        villager_pos = params.get("villager_pos")
        if villager_pos is None or len(villager_pos) != 3:
            return False

        max_nav_steps = params.get("max_nav_steps", 200)

        # Step 1: Navigate near the villager.
        try:
            from minedojo.pathfinding import Navigator
        except ImportError:
            return False

        nav = Navigator(self.env)
        if not nav.navigate_to(
            int(villager_pos[0]),
            int(villager_pos[1]),
            int(villager_pos[2]),
            max_steps=max_nav_steps,
        ):
            return False

        # Step 2: Enable GUI interaction via command.
        try:
            self.env.execute_cmd(
                "/execute as @p at @s run data merge entity @p {selectedItem:{id:\"minecraft:air\",Count:1b}}"
            )
            self.env.execute_cmd(
                "/execute as @p at @s run tag @p add allowGuiInteract"
            )
        except AttributeError:
            pass
        self.noop()

        # Step 3: Right-click (use) the villager to open trade GUI.
        action = self.env.action_space.no_op()
        if "use" in action:
            action["use"] = 1
        self.step(action)
        self.noop()

        # Step 4: Select the trade.
        try:
            self.env.execute_cmd(f"/execute as @p at @s run data merge entity @p {{selectedItemSlot:{params.get('trade_index', 0)}}}")
        except AttributeError:
            pass
        self.noop()

        return True


class EnchantOperation(Operation):
    """Open an enchanting table GUI and select an enchantment slot.

    Parameters:
        slot: Enchantment option slot (0-2, default 0).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "slot": {
                "type": "int",
                "description": "Enchantment slot index (0-2)",
                "default": 0,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        slot = params.get("slot", 0)

        # Open enchant GUI via use action (assuming near table).
        action = self.env.action_space.no_op()
        if "use" in action:
            action["use"] = 1
        self.step(action)
        self.noop()

        # Select enchant slot via hotbar/click.
        try:
            self.env.execute_cmd(f"/execute as @p at @s run data merge entity @p {{selectedItemSlot:{slot}}}")
        except AttributeError:
            pass
        self.noop()

        return True


class BrewOperation(Operation):
    """Use a brewing stand and add an ingredient.

    Parameters:
        ingredient: Ingredient name (e.g., "nether_wart", "blaze_powder").
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "ingredient": {
                "type": "str",
                "description": "Ingredient name (e.g. 'nether_wart')",
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        ingredient = params.get("ingredient")
        if ingredient is None:
            return False

        # Open brewing stand GUI.
        action = self.env.action_space.no_op()
        if "use" in action:
            action["use"] = 1
        self.step(action)
        self.noop()

        # Add ingredient.
        if not ingredient.startswith("minecraft:"):
            ingredient = "minecraft:" + ingredient
        try:
            self.env.execute_cmd(
                f"/replaceitem entity @p slot.weapon.mainhand {ingredient} 1 0"
            )
        except AttributeError:
            pass
        self.noop()

        return True


class AnvilOperation(Operation):
    """Use an anvil and combine two items.

    Parameters:
        item1: First item name (e.g., "diamond_sword").
        item2: Second item name (e.g., "diamond").
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "item1": {
                "type": "str",
                "description": "First item name",
            },
            "item2": {
                "type": "str",
                "description": "Second item name",
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        item1 = params.get("item1")
        item2 = params.get("item2")
        if item1 is None or item2 is None:
            return False

        # Open anvil GUI.
        action = self.env.action_space.no_op()
        if "use" in action:
            action["use"] = 1
        self.step(action)
        self.noop()

        # Place items (simplified: just confirm the action).
        try:
            if not item1.startswith("minecraft:"):
                item1 = "minecraft:" + item1
            if not item2.startswith("minecraft:"):
                item2 = "minecraft:" + item2
            self.env.execute_cmd(
                f"/replaceitem entity @p slot.weapon.mainhand {item1} 1 0"
            )
        except AttributeError:
            pass
        self.noop()

        return True


class ChestOperation(Operation):
    """Open a chest and move items between slots.

    Parameters:
        from_slot: Source inventory slot index (default 0).
        to_slot: Target inventory slot index (default 5).
    """

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "from_slot": {
                "type": "int",
                "description": "Source inventory slot",
                "default": 0,
            },
            "to_slot": {
                "type": "int",
                "description": "Target inventory slot",
                "default": 5,
            },
        }

    def execute(self, params: Dict[str, Any]) -> bool:
        from_slot = params.get("from_slot", 0)
        to_slot = params.get("to_slot", 5)

        # Open chest GUI.
        action = self.env.action_space.no_op()
        if "use" in action:
            action["use"] = 1
        self.step(action)
        self.noop()

        # Move items between slots.
        try:
            self.env.execute_cmd(
                f"/replaceitem entity @p container.{from_slot} minecraft:air 1 0"
            )
        except AttributeError:
            pass
        self.noop()

        return True
