"""Snapshot builder for creating pre-configured Minecraft world snapshots.

Provides :class:`SnapshotBuilder` which creates a :class:`~minedojo.sim.sim.MineDojoSim`
environment configured per a :class:`~minedojo.world_snapshots.config.SceneConfig`,
runs any scene-specific setup (building structures, placing blocks, spawning mobs),
saves the resulting world to disk, and tears down the environment.

Scene-specific setup functions are registered in the ``_SETUP_FUNCTIONS`` registry
keyed by the ``extra_setup`` field of the :class:`SceneConfig`.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from minedojo.sim import MineDojoSim
from minedojo.sim.inventory import InventoryItem
from minedojo.world_snapshots.config import SceneConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry of scene-specific setup functions
# ---------------------------------------------------------------------------

_SETUP_FUNCTIONS: Dict[str, callable] = {}


def _register(name: str):
    """Decorator that registers a setup function under *name*."""

    def decorator(func):
        _SETUP_FUNCTIONS[name] = func
        return func

    return decorator


# ---------------------------------------------------------------------------
# Scene-specific setup functions
# ---------------------------------------------------------------------------


@_register("setup_village")
def setup_village(env: MineDojoSim) -> None:
    """Village setup — spawn-in-village is handled at construction time.

    No additional commands needed; the ``spawn_in_village=True`` flag on
    :class:`~minedojo.sim.sim.MineDojoSim` causes Malmo to place the agent
    inside a village automatically.
    """
    pass


@_register("setup_cave")
def setup_cave(env: MineDojoSim) -> None:
    """Build an enclosed dark cave on a flat world.

    Constructs a room with stone walls, floor, and ceiling around the
    agent.  The resulting space has no natural light, making it suitable
    for testing torch placement and mining in darkness.

    Room dimensions match the cave scene's spawn region (interior 11x4x11
    blocks) so the agent cannot escape.
    """
    stone = "minecraft:stone"
    blocks: List[str] = []
    positions: List[List[int]] = []

    # --- Floor (y = -1 relative to agent) ---
    for x in range(-5, 6):
        for z in range(-5, 6):
            blocks.append(stone)
            positions.append([x, -1, z])

    # --- Ceiling (y = +4 relative to agent) ---
    for x in range(-5, 6):
        for z in range(-5, 6):
            blocks.append(stone)
            positions.append([x, 4, z])

    # --- Walls (y = 0..3 relative to agent) ---
    for y in range(0, 4):
        for x in range(-5, 6):
            # North wall (z = -5)
            blocks.append(stone)
            positions.append([x, y, -5])
            # South wall (z = +5)
            blocks.append(stone)
            positions.append([x, y, 5])
        for z in range(-4, 5):
            # West wall (x = -5), skip corners already placed
            blocks.append(stone)
            positions.append([-5, y, z])
            # East wall (x = +5)
            blocks.append(stone)
            positions.append([5, y, z])

    env.set_block(blocks, positions)


@_register("setup_water")
def setup_water(env: MineDojoSim) -> None:
    """Build a small wooden platform at the agent's spawn point in the ocean.

    Places a 5x5 oak-planks platform at the agent's feet so the agent stands
    on solid ground instead of treading water.  Without this, the agent
    drowns within ~30 steps of spawning in an ocean biome.
    """
    planks = "minecraft:planks"
    blocks: List[str] = []
    positions: List[List[int]] = []
    for x in range(-2, 3):
        for z in range(-2, 3):
            blocks.append(planks)
            positions.append([x, -1, z])
    env.set_block(blocks, positions)


@_register("setup_gui_room")
def setup_gui_room(env: MineDojoSim) -> None:
    """Build a flat room and place GUI interaction blocks.

    Places the following around the agent at ground level:

    ================  ===============
    Block             Relative Position
    ================  ===============
    Crafting Table    ( 2, 0,  0)
    Furnace           (-2, 0,  0)
    Enchanting Table  ( 0, 0,  2)
    Anvil             ( 0, 0, -2)
    Brewing Stand     ( 1, 0,  1)
    Double Chest      (-1, 0, -1)
    ================  ===============

    Also spawns 3 villagers nearby so the ``"trade"`` operation can be tested.
    """
    # Place GUI blocks at fixed relative positions around the agent
    gui_placements = [
        ("minecraft:crafting_table", [2, 0, 0]),
        ("minecraft:furnace", [-2, 0, 0]),
        ("minecraft:enchanting_table", [0, 0, 2]),
        ("minecraft:anvil", [0, 0, -2]),
        ("minecraft:brewing_stand", [1, 0, 1]),
        ("minecraft:chest", [-1, 0, -1]),
        # Second chest block to form a double chest (adjacent)
        ("minecraft:chest", [-2, 0, -1]),
    ]
    blocks = [b for b, _ in gui_placements]
    positions = [p for _, p in gui_placements]
    env.set_block(blocks, positions)

    # Pre-fill the first chest (at relative position -1, 0, -1) with a few
    # useful items so the agent can interact with a non-empty container.
    _fill_chest(env, rel_x=-1, rel_y=0, rel_z=-1)

    # Spawn 3 villagers for trading
    villager_positions = [[3, 0, 0], [0, 0, 3], [-3, 0, 0]]
    env.spawn_mobs(
        mobs=["minecraft:villager"] * len(villager_positions),
        rel_positions=villager_positions,
    )


def _fill_chest(env: MineDojoSim, rel_x: int, rel_y: int, rel_z: int) -> None:
    """Fill a chest at the given relative position with starter items.

    Uses ``/replaceitem block`` to populate container slots of the chest.
    """
    chest_items = [
        ("minecraft:diamond", 3, 0),
        ("minecraft:iron_ingot", 5, 0),
        ("minecraft:emerald", 2, 0),
        ("minecraft:dye", 16, 4),  # lapis_lazuli = dye with damage 4 in MC 1.11.2
    ]
    for slot_idx, (item, qty, data) in enumerate(chest_items):
        cmd = (
            f"/replaceitem block "
            f"~{rel_x} ~{rel_y} ~{rel_z} "
            f"container.{slot_idx} {item} {qty} {data}"
        )
        env.execute_cmd(cmd)


# ---------------------------------------------------------------------------
# SnapshotBuilder
# ---------------------------------------------------------------------------


class SnapshotBuilder:
    """Creates and saves a world snapshot for a given scene configuration.

    The builder:
    1.  Constructs a :class:`~minedojo.sim.sim.MineDojoSim` with the world
        type, biome, inventory, and other options specified by the
        :class:`~minedojo.world_snapshots.config.SceneConfig`.
    2.  Resets the environment to generate the world.
    3.  Runs any extra setup registered under the config's ``extra_setup`` key.
    4.  Sets the time to day (6000) and weather to clear.
    5.  Saves the world to *output_path* via :meth:`MineDojoSim.save_snapshot`.
    6.  Closes the environment.

    Parameters:
        scene_config: The scene configuration to build.
        image_size: Observation image size passed to MineDojoSim.
        seed: Optional random seed for reproducibility.
    """

    def __init__(
        self,
        scene_config: SceneConfig,
        image_size: Union[int, Tuple[int, int]] = (160, 256),
        seed: Optional[int] = None,
    ):
        self.config = scene_config
        self.image_size = image_size
        self.seed = seed
        self._env: Optional[MineDojoSim] = None

    def _create_env(self) -> MineDojoSim:
        """Build the :class:`MineDojoSim` instance from the scene config."""
        config = self.config
        kwargs: dict = {
            "image_size": self.image_size,
            "seed": self.seed,
            # Also seed world generation so builds are reproducible — important
            # for the village scene, where VillageSpawnDecorator only succeeds
            # if a village happens to generate near spawn (seed-dependent).
            "world_seed": self.seed,
            "sim_name": f"snapshot_{config.name}",
        }

        # World generation
        kwargs["generate_world_type"] = config.world_type
        if config.world_type == "specified_biome":
            kwargs["specified_biome"] = config.biome
        elif config.world_type == "flat":
            kwargs["regenerate_world_after_reset"] = True
        elif config.world_type == "default":
            # force_reset=True so DefaultWorldGenerator actually flushes the
            # world to saves/ (with force_reset=False the world is not
            # persisted and save_snapshot copies an empty directory).
            kwargs["regenerate_world_after_reset"] = True

        # Village spawning is managed via the extra_setup mechanism
        if config.extra_setup == "setup_village":
            kwargs["spawn_in_village"] = True

        # Starting inventory: convert plain dicts to InventoryItem tuples
        if config.default_inventory:
            kwargs["initial_inventory"] = [
                InventoryItem(
                    slot=idx,
                    name=item["type"],
                    variant=item.get("variant"),
                    quantity=item.get("quantity", 1),
                )
                for idx, item in enumerate(config.default_inventory)
            ]

        # Start time and weather (applied after reset in build())
        kwargs["start_time"] = 6000
        kwargs["initial_weather"] = "clear"

        return MineDojoSim(**kwargs)

    def build(self, output_path: str) -> None:
        """Create the world, run scene setup, and save the snapshot.

        Parameters:
            output_path: Directory path where the world snapshot will be saved.

        Raises:
            RuntimeError: If the environment fails to reset or save.
        """
        import time

        logger.info("Building snapshot for scene '%s' ...", self.config.name)

        # 1. Create environment
        self._env = self._create_env()
        logger.info("Environment created for scene '%s'.", self.config.name)

        # 2. Reset to generate the world
        logger.info("Resetting environment ...")
        self._env.reset()
        time.sleep(1)

        # 3. Run extra scene-specific setup
        extra_setup = self.config.extra_setup
        if extra_setup is not None:
            setup_fn = _SETUP_FUNCTIONS.get(extra_setup)
            if setup_fn is None:
                raise ValueError(
                    f"Unknown extra_setup function '{extra_setup}'. "
                    f"Registered functions: {list(_SETUP_FUNCTIONS.keys())}"
                )
            logger.info("Running extra setup: %s ...", extra_setup)
            setup_fn(self._env)
            time.sleep(1)

        # 4. Ensure time and weather are set correctly
        self._env.set_time(6000)
        self._env.set_weather("clear")

        # 5. Save snapshot
        logger.info("Saving snapshot to '%s' ...", output_path)
        self._env.execute_cmd("/save-all")
        time.sleep(2)
        self._env.save_snapshot(output_path)
        logger.info("Snapshot saved successfully to '%s'.", output_path)

        # 6. Close environment
        self.close()

    def close(self) -> None:
        """Close the underlying Minecraft environment if it is still open."""
        if self._env is not None:
            try:
                self._env.close()
            except Exception as exc:
                logger.warning("Error closing environment: %s", exc)
            finally:
                self._env = None

    def __del__(self):
        """Ensure the environment is closed when the builder is garbage collected."""
        self.close()
