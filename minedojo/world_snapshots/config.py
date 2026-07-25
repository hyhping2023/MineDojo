"""Scene configuration definitions for MineDojo world snapshots.

Defines :class:`SceneConfig` — a dataclass that specifies the world type,
biome, spawn region, default inventory, allowed operations, and any
scene-specific setup required to build a ready-to-use Minecraft world snapshot.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SceneConfig:
    """Configuration for a single Minecraft scene / world type.

    Attributes:
        name: Unique scene identifier (e.g. ``"plains"``, ``"cave"``).
        world_type: One of ``"specified_biome"``, ``"default"``, or ``"flat"`` —
            passed directly to :class:`~minedojo.sim.sim.MineDojoSim` as
            ``generate_world_type``.
        biome: If *world_type* is ``"specified_biome"``, the biome name
            (e.g. ``"plains"``, ``"forest"``); otherwise ``None``.
        spawn_region: Bounding box ``{xmin, xmax, ymin, ymax, zmin, zmax}``
            describing the valid spawn area for the agent.
        extra_setup: Optional identifier for a scene-specific setup routine
            (e.g. ``"setup_cave"``, ``"setup_gui_room"``) that will be called
            after world generation.  ``None`` if no extra setup is needed.
        default_inventory: List of item dicts ``{"type": ..., "quantity": ...}``
            to place in the agent's starting inventory.
        operation_whitelist: Names of operations that are valid in this scene
            (e.g. ``"navigate"``, ``"attack"``, ``"craft"``).
    """

    name: str
    world_type: str
    biome: Optional[str] = None
    spawn_region: Dict[str, int] = field(default_factory=dict)
    extra_setup: Optional[str] = None
    default_inventory: List[Dict[str, Any]] = field(default_factory=list)
    operation_whitelist: List[str] = field(default_factory=list)


SCENE_CONFIGS: Dict[str, SceneConfig] = {
    "plains": SceneConfig(
        name="plains",
        world_type="specified_biome",
        biome="plains",
        spawn_region={
            "xmin": -100,
            "xmax": 100,
            "ymin": 63,
            "ymax": 72,
            "zmin": -100,
            "zmax": 100,
        },
        default_inventory=[{"type": "diamond_pickaxe", "quantity": 1}],
        operation_whitelist=[
            "navigate",
            "mine_block",
            "spawn_entity",
            "attack",
            "craft",
            "place_block",
            "open_inventory",
        ],
    ),
    "forest": SceneConfig(
        name="forest",
        world_type="specified_biome",
        biome="forest",
        spawn_region={
            "xmin": -100,
            "xmax": 100,
            "ymin": 63,
            "ymax": 72,
            "zmin": -100,
            "zmax": 100,
        },
        default_inventory=[{"type": "diamond_axe", "quantity": 1}],
        operation_whitelist=[
            "navigate",
            "mine_block",
            "spawn_entity",
            "attack",
            "craft",
            "place_block",
        ],
    ),
    "extreme_hills": SceneConfig(
        name="extreme_hills",
        world_type="specified_biome",
        biome="extreme_hills",
        spawn_region={
            "xmin": -100,
            "xmax": 100,
            "ymin": 63,
            "ymax": 120,
            "zmin": -100,
            "zmax": 100,
        },
        default_inventory=[{"type": "diamond_pickaxe", "quantity": 1}],
        operation_whitelist=[
            "navigate",
            "mine_block",
            "spawn_entity",
            "attack",
        ],
    ),
    "village": SceneConfig(
        name="village",
        world_type="default",
        biome=None,
        spawn_region={
            "xmin": -50,
            "xmax": 50,
            "ymin": 63,
            "ymax": 72,
            "zmin": -50,
            "zmax": 50,
        },
        default_inventory=[{"type": "diamond_sword", "quantity": 1}],
        operation_whitelist=[
            "navigate",
            "trade",
            "attack",
            "open_inventory",
            "craft",
        ],
        extra_setup="setup_village",
    ),
    "cave": SceneConfig(
        name="cave",
        world_type="flat",
        biome=None,
        spawn_region={
            "xmin": -5,
            "xmax": 5,
            "ymin": 5,
            "ymax": 10,
            "zmin": -5,
            "zmax": 5,
        },
        default_inventory=[
            {"type": "torch", "quantity": 64},
            {"type": "diamond_pickaxe", "quantity": 1},
        ],
        operation_whitelist=[
            "navigate",
            "mine_block",
            "spawn_entity",
            "attack",
        ],
        extra_setup="setup_cave",
    ),
    "water": SceneConfig(
        name="water",
        world_type="specified_biome",
        biome="ocean",
        spawn_region={
            "xmin": -50,
            "xmax": 50,
            "ymin": 63,
            "zmin": -50,
            "zmax": 50,
        },
        default_inventory=[{"type": "boat", "quantity": 1}],
        operation_whitelist=["navigate", "spawn_entity"],
    ),
    "gui_item": SceneConfig(
        name="gui_item",
        world_type="flat",
        biome=None,
        spawn_region={
            "xmin": -3,
            "xmax": 3,
            "ymin": 5,
            "ymax": 5,
            "zmin": -3,
            "zmax": 3,
        },
        default_inventory=[
            {"type": "diamond_sword", "quantity": 1},
            {"type": "iron_ingot", "quantity": 10},
            {"type": "diamond", "quantity": 5},
            {"type": "lapis_lazuli", "quantity": 64},
            {"type": "bottle", "quantity": 64},
            {"type": "nether_wart", "quantity": 64},
            {"type": "diamond_helmet", "quantity": 1},
        ],
        operation_whitelist=[
            "navigate",
            "trade",
            "enchant",
            "brew",
            "anvil",
            "chest",
            "craft",
            "smelt",
            "open_inventory",
        ],
        extra_setup="setup_gui_room",
    ),
}
