"""Operation registry maps operation names to their classes."""

from .movement import NavigateOperation, LookAtOperation, StrafeOperation
from .inventory import (
    OpenInventoryOperation,
    CloseInventoryOperation,
    SelectItemOperation,
    DropItemOperation,
)
from .craft import CraftOperation, SmeltOperation
from .combat import AttackOperation, SpawnAttackOperation
from .mining import MineBlockOperation, ChopTreeOperation
from .placement import PlaceBlockOperation
from .gui import (
    TradeOperation,
    EnchantOperation,
    BrewOperation,
    AnvilOperation,
    ChestOperation,
)
from .entities import SpawnEntityOperation, InteractEntityOperation, MountOperation

OPERATION_REGISTRY = {
    "navigate": NavigateOperation,
    "look_at": LookAtOperation,
    "strafe": StrafeOperation,
    "open_inventory": OpenInventoryOperation,
    "close_inventory": CloseInventoryOperation,
    "select_item": SelectItemOperation,
    "drop_item": DropItemOperation,
    "craft": CraftOperation,
    "smelt": SmeltOperation,
    "attack": AttackOperation,
    "spawn_attack": SpawnAttackOperation,
    "mine_block": MineBlockOperation,
    "chop_tree": ChopTreeOperation,
    "place_block": PlaceBlockOperation,
    "trade": TradeOperation,
    "enchant": EnchantOperation,
    "brew": BrewOperation,
    "anvil": AnvilOperation,
    "chest": ChestOperation,
    "spawn_entity": SpawnEntityOperation,
    "interact_entity": InteractEntityOperation,
    "mount": MountOperation,
}
