"""Programmatic task generation for diverse video sequences.

Provides :class:`TaskGenerator` which creates batches of
:class:`~minedojo.workers.task.VideoTask` objects with randomized
operations across different scene types — movement sequences, combat
encounters, crafting chains, and mixed combinations.
"""

import random
from typing import List

from .task import VideoTask
from minedojo.world_snapshots.config import SCENE_CONFIGS


class TaskGenerator:
    """Generates diverse :class:`VideoTask` specifications programmatically.

    Tasks are created with randomized parameters (target positions, mob
    types, weapons, etc.) so that generated videos exhibit varied agent
    behavior.  Each generation method accepts a *count* to control the
    number of tasks produced per scene type.

    Example::

        gen = TaskGenerator()
        tasks = gen.generate_batch(n=100, scene_types=["plains", "cave"])
    """

    # ------------------------------------------------------------------
    # Pre-defined mob and weapon pools
    # ------------------------------------------------------------------

    MOB_POOL = [
        "minecraft:zombie",
        "minecraft:skeleton",
        "minecraft:spider",
        "minecraft:creeper",
        "minecraft:witch",
        "minecraft:enderman",
    ]

    WEAPON_POOL = [
        "diamond_sword",
        "iron_sword",
        "stone_sword",
        "diamond_axe",
        "iron_axe",
    ]

    TOOL_POOL = [
        "diamond_pickaxe",
        "iron_pickaxe",
        "stone_pickaxe",
        "diamond_axe",
        "iron_axe",
    ]

    # ------------------------------------------------------------------
    # Task generators per category
    # ------------------------------------------------------------------

    def random_movement_task(
        self, scene_type: str, count: int = 1, max_steps: int = 200
    ) -> List[VideoTask]:
        """Generate navigation-only tasks with random target positions.

        Parameters:
            scene_type: Scene config key (e.g. ``"plains"``).
            count: Number of tasks to generate.
            max_steps: Maximum steps per navigation operation.

        Returns:
            List of :class:`VideoTask` objects.
        """
        tasks = []
        for i in range(count):
            target = [
                random.randint(-20, 20),
                63,
                random.randint(-20, 20),
            ]
            tasks.append(VideoTask(
                task_id=f"movement_{scene_type}_{i}",
                scene_type=scene_type,
                operations=[
                    ("navigate", {"target": target, "max_steps": max_steps}),
                ],
                metadata={
                    "type": "movement",
                    "scene": scene_type,
                    "target": target,
                },
            ))
        return tasks

    def random_combat_task(
        self, scene_type: str, count: int = 1
    ) -> List[VideoTask]:
        """Generate combat tasks with random mob + weapon combinations.

        Parameters:
            scene_type: Scene config key.
            count: Number of tasks to generate.
        """
        tasks = []
        for i in range(count):
            mob = random.choice(self.MOB_POOL)
            weapon = random.choice(self.WEAPON_POOL)
            tasks.append(VideoTask(
                task_id=f"combat_{scene_type}_{i}",
                scene_type=scene_type,
                operations=[
                    ("spawn_attack", {
                        "mob": mob,
                        "rel_pos": [random.randint(3, 8), 0, random.randint(-2, 2)],
                        "weapon": weapon,
                    }),
                ],
                metadata={
                    "type": "combat",
                    "scene": scene_type,
                    "mob": mob,
                    "weapon": weapon,
                },
            ))
        return tasks

    def random_craft_task(
        self, scene_type: str, count: int = 1
    ) -> List[VideoTask]:
        """Generate crafting tasks (requires gui_item or similarly equipped scene).

        Parameters:
            scene_type: Scene config key.
            count: Number of tasks to generate.
        """
        craft_options = [
            ("craft", {"recipe": "crafting_table",
                       "ingredients": ["wooden_planks", "wooden_planks",
                                       "wooden_planks", "wooden_planks"]}),
            ("craft", {"recipe": "wooden_pickaxe",
                       "ingredients": ["wooden_planks", "wooden_planks", "stick"]}),
            ("smelt", {"item": "iron_ore", "fuel": "coal"}),
        ]
        tasks = []
        for i in range(count):
            op_name, op_params = random.choice(craft_options)
            tasks.append(VideoTask(
                task_id=f"craft_{scene_type}_{i}",
                scene_type=scene_type,
                operations=[(op_name, op_params)],
                metadata={
                    "type": "craft",
                    "scene": scene_type,
                    "operation": op_name,
                },
            ))
        return tasks

    def random_mine_task(
        self, scene_type: str, count: int = 1
    ) -> List[VideoTask]:
        """Generate mining tasks with random block types and positions.

        Parameters:
            scene_type: Scene config key.
            count: Number of tasks to generate.
        """
        mine_blocks = [
            "minecraft:stone",
            "minecraft:dirt",
            "minecraft:log",
            "minecraft:coal_ore",
        ]
        tasks = []
        for i in range(count):
            block = random.choice(mine_blocks)
            tasks.append(VideoTask(
                task_id=f"mine_{scene_type}_{i}",
                scene_type=scene_type,
                operations=[
                    ("navigate", {
                        "target": [random.randint(-10, 10), 63,
                                   random.randint(-10, 10)],
                        "max_steps": 100,
                    }),
                    ("mine_block", {
                        "block_type": block,
                        "rel_pos": [random.randint(1, 5), 0,
                                    random.randint(-2, 2)],
                    }),
                ],
                metadata={
                    "type": "mine",
                    "scene": scene_type,
                    "block": block,
                },
            ))
        return tasks

    def random_entity_task(
        self, scene_type: str, count: int = 1
    ) -> List[VideoTask]:
        """Generate entity spawning and interaction tasks.

        Parameters:
            scene_type: Scene config key.
            count: Number of tasks to generate.
        """
        entities = [
            "minecraft:cow",
            "minecraft:pig",
            "minecraft:sheep",
            "minecraft:chicken",
        ]
        tasks = []
        for i in range(count):
            entity = random.choice(entities)
            tasks.append(VideoTask(
                task_id=f"entity_{scene_type}_{i}",
                scene_type=scene_type,
                operations=[
                    ("spawn_entity", {
                        "mob": entity,
                        "rel_pos": [random.randint(2, 6), 0,
                                    random.randint(-2, 2)],
                    }),
                ],
                metadata={
                    "type": "entity",
                    "scene": scene_type,
                    "entity": entity,
                },
            ))
        return tasks

    # ------------------------------------------------------------------
    # Batch generation
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        n: int,
        scene_types: List[str] = None,
    ) -> List[VideoTask]:
        """Generate a balanced batch of *n* tasks across scene types.

        Tasks are distributed evenly across scene types, with a mix of
        movement, combat, mining, and entity interaction tasks.

        Parameters:
            n: Total number of tasks to generate.
            scene_types: Scene types to use (default: all registered types).

        Returns:
            List of :class:`VideoTask` objects.
        """
        if scene_types is None:
            scene_types = list(SCENE_CONFIGS.keys())

        tasks = []
        per_scene = max(1, n // len(scene_types))

        for st in scene_types:
            tasks.extend(self.random_movement_task(st, max(1, per_scene // 4)))
            tasks.extend(self.random_combat_task(st, max(1, per_scene // 4)))
            tasks.extend(self.random_mine_task(st, max(1, per_scene // 4)))
            tasks.extend(self.random_entity_task(st, max(1, per_scene // 4)))

            # Only generate craft tasks for scenes that support it
            cfg = SCENE_CONFIGS.get(st)
            if cfg and "craft" in cfg.operation_whitelist:
                tasks.extend(self.random_craft_task(st, max(1, per_scene // 4)))

        # Trim to exactly n tasks
        if len(tasks) > n:
            tasks = random.sample(tasks, n)

        return tasks
