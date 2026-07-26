# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Common Commands

```bash
# Install from source (editable mode). Requires JDK 8 for Minecraft backend.
pip install -e .

# Validate installation (creates an env and runs 20 steps).
# First run compiles the Java Malmo mod via Gradle — this can be slow.
python scripts/validate_install.py

# Headless mode (when no display is available)
MINEDOJO_HEADLESS=1 python scripts/validate_install.py
# --- OR ---
xvfb-run python scripts/validate_install.py

# Validate the extension modules (operations, pathfinding, world_snapshots, workers).
# Smoke-tests imports, runs A* on a synthetic grid, checks the operation registry
# and scene configs. Does not launch Minecraft.
python scripts/validate_extension.py

# Build all 7 world snapshots (or pass --scene <name> for one) for use by the
# parallel video generation workers.
python scripts/build_snapshots.py --output /data/snapshots/

# Launch parallel video generation workers.
python -m minedojo.workers.main --snapshots-dir /data/snapshots/ --output-dir /data/videos/ --n-workers 8
```

There are no tests, linters, or CI configuration in this repository. `pytest` is listed in `requirements.txt` but no test files exist.

## Architecture

MineDojo is a Gymnasium-style Minecraft simulation framework for embodied agent research. Python >= 3.10, tested on Ubuntu 20.04 and macOS. Uses `gymnasium>=1.3` (not `gym`): `MineDojoSim` extends `gymnasium.Env` and `MetaTaskBase` extends `gymnasium.Wrapper`. `step()` returns the 5-tuple `(obs, reward, terminated, truncated, info)`.

### Entry Point

`minedojo/__init__.py` exports `make` from `minedojo/tasks/__init__.py`. Users call:

```python
import minedojo
env = minedojo.make(task_id="combat_spider_plains_leather_armors_diamond_sword_shield", image_size=(160, 256))
```

`make(task_id, *args, cam_interval=15, **kwargs)` is the factory. `cam_interval` controls camera-action discretization in the ARNN wrapper; all other kwargs (`image_size`, `world_seed`, `seed`, `generate_world_type`, `world_file_path`, `use_voxel`, `voxel_size`, etc.) are forwarded to `MineDojoSim`. Every env returned by `make()` is wrapped in `ARNNWrapper`.

### Layer Stack (top to bottom)

```
minedojo.make() → ARNNWrapper → MetaTaskBase (or MineDojoSim) → FastResetWrapper? → MineDojoSim → BridgeEnv → Malmo (Java)
```

1. **Task Layer** (`minedojo/tasks/`) — Task definitions, prompts, guidance, reward/success logic.
2. **Wrapper Layer** (`minedojo/sim/wrappers/`) — ARNNWrapper (camera discretization + action masks + delta inventory obs). FastResetWrapper for `/kill`-based resets.
3. **Simulation Layer** (`minedojo/sim/`) — MineDojoSim (extends `gymnasium.Env`), configures handlers, delegates to BridgeEnv.
4. **Bridge Layer** (`minedojo/sim/bridge/`) — Pyro4 RPC between Python and the Java Minecraft Malmo mod.
5. **Malmo Mod** (`minedojo/sim/Malmo/`) — Vendored Java Minecraft Forge mod. Version `0.37.0` (see `minedojo/sim/Malmo/VERSION`). Compiled via Gradle.

### Task System (`minedojo/tasks/`)

`minedojo/tasks/__init__.py` is the central registry (~535 lines). It:
- Loads YAML task specs from `description_files/` using OmegaConf
- Performs variable substitution to generate 1000s of programmatic tasks (biomes, mobs, materials, etc.)
- Supports three task families plus meta tasks:

| Task Type | Class | File |
|-----------|-------|------|
| Harvest | `HarvestMeta` | `meta/harvest.py` |
| Combat | `CombatMeta` | `meta/combat.py` |
| TechTree | `TechTreeMeta` | `meta/tech_tree.py` |
| Survival | `SurvivalMeta` | `meta/survival.py` |
| Creative | `CreativeMeta` | `meta/creative/` (directory) |
| Playthrough | `Playthrough` | `meta/playthrough.py` |
| Open-Ended | `MineDojoSim` (raw) | `sim/sim.py` |

All meta tasks extend `MetaTaskBase` (or `ExtraSpawnMetaTaskBase` in `meta/extra_spawn.py`), which extends `gymnasium.Wrapper` and wraps `MineDojoSim`. MetaTaskBase adds reward computation, success criteria checking, prompt/guidance management, and optional fast reset.

Every environment returned by `make()` is wrapped in `ARNNWrapper` (from `minedojo/sim/wrappers/ar_nn/`) which:
- Discretizes continuous camera actions
- Converts the multi-discrete action space to a flat categorical space for neural networks
- Provides action masks for invalid actions
- Computes delta inventory observations

### Simulation (`minedojo/sim/`)

**MineDojoSim** (`sim.py`) extends `gymnasium.Env`. It:
- Assembles observation handlers, action handlers, world generator handlers, and server handlers
- Serializes the configuration to a Malmo mission XML via `ConfigSimSpec.to_xml()`
- Delegates environment stepping to `BridgeEnv`
- Provides Minecraft command wrappers: `spawn_mobs()`, `set_block()`, `teleport_agent()`, `set_inventory()`, `set_time()`, `set_weather()`, `random_teleport()`, `save_snapshot()`, `execute_cmd()`, etc.
- Supports `generate_world_type="from_file"` with `world_file_path` to load a pre-built world snapshot via Malmo's `FileWorldGenerator` (emitted by `handlers/server/world.py`).

**Handler system** (`handlers/`) — All handlers extend `Handler` (in `handler.py`) which uses Jinja2 templates for XML generation. Handlers are organized into:
- `handlers/agent/observations/` — POV, inventory, equipment, life stats, location, voxels, lidar, damage source, achievements, nearby tools
- `handlers/agent/actions/` — Camera, craft, smelt, equip, place, keyboard commands, swap slot
- `handlers/server/` — World generation, initial conditions, quit conditions, navigation

**Bridge** (`bridge/`) — `BridgeEnv` manages the Python-Java connection via Pyro4. `MCInstance` manages the Minecraft process lifecycle (launch, monitor via watchdog, cleanup). Socket communication is handled by `socket_comm.py`.

**Malmo mod** (`Malmo/`) — Java source at `Malmo/Minecraft/src/main/java/com/microsoft/Malmo/`. Key packages: `Client/` (Java-side Pyro4 client), `MissionHandlers/` (Java-side handler implementations), `Mixins/` (vanilla Minecraft bytecode patches), `Server/`, `Utils/`. The mod is launched via `launch_minecraft_in_background.py`.

### Data Module (`minedojo/data/`)

Knowledge base dataset loaders: `RedditDataset`, `WikiDataset`, `YouTubeDataset`. These fetch the internet-scale knowledge base (730K YouTube videos, 7K Wiki pages, 340K Reddit posts) used for training MineCLIP (in the separate MineCLIP repo).

## Extensions

Four top-level modules beyond the core sim/task stack. They are smoke-tested by `scripts/validate_extension.py`.

### Operations Framework (`minedojo/operations/`)

22 scripted operation types covering all major Minecraft interactions. Each operation subclasses `Operation` (`base.py`) and implements `get_parameters()` / `execute(params) -> bool`. Operations are registered by string name in `OPERATION_REGISTRY` (`registry.py`).

| Category | File | Operations |
|----------|------|------------|
| Movement | `movement.py` | `navigate`, `look_at`, `strafe` |
| Inventory | `inventory.py` | `open_inventory`, `close_inventory`, `select_item`, `drop_item` |
| Crafting | `craft.py` | `craft`, `smelt` |
| Combat | `combat.py` | `attack`, `spawn_attack` |
| Mining | `mining.py` | `mine_block`, `chop_tree` |
| Placement | `placement.py` | `place_block` |
| GUI | `gui.py` | `trade`, `enchant`, `brew`, `anvil`, `chest` |
| Entities | `entities.py` | `spawn_entity`, `interact_entity`, `mount` |

`OperationSequencer(env).run_sequence(ops, max_steps)` runs a list of `(op_name, params)` tuples, stops on first failure, and collects POV frames from `env.prev_obs["pov"]`. GUI operations issue Minecraft slash-commands via `env.execute_cmd()` (e.g. `/replaceitem`, `/data merge`), which are routed by the Java Malmo `MissionHandlers`.

### Pathfinding (`minedojo/pathfinding/`)

A* pathfinding on a 3D voxel occupancy grid.

- `Navigator(env).navigate_to(x, y, z, max_steps=500) -> bool` is the high-level entry point. It requires the env to be created with `use_voxel=True` and a `voxel_size`; if `obs["voxels"]` is missing, pathfinding is a no-op.
- `VoxelMap` (`voxel_map.py`) is a sparse `defaultdict` keyed by integer `(x, y, z)`, built incrementally by `update(obs)` converting local Fortran-order voxel arrays to world block coordinates using the agent's feet position.
- `astar.py` supports straight, diagonal (only if both adjacent straight cells passable), jump-up, forward-jump-up, step-down, and safe-fall neighbor moves. Water incurs a 4x cost penalty unless the goal is in water.
- `controller.py`'s `PathFollower.get_action(...)` turns the next waypoint into a discrete env action. The navigator replans every `replan_interval` steps (default 5) as new terrain is discovered.

### Parallel Video Generation (`minedojo/workers/`)

Multi-process workers that reuse Minecraft instances across tasks for high-throughput video generation.

- `TaskScheduler` (`scheduler.py`) owns `task_queue`/`result_queue` (`multiprocessing.Queue`), launches `n_workers` `VideoWorker` processes, and distributes `VideoTask`s via `submit`/`submit_batch`/`collect_results`.
- `VideoTask`/`TaskResult` (`task.py`) are dataclasses carrying `(task_id, scene_type, operations, max_steps, metadata)` and `(task_id, video_path, success, frames, duration_seconds, errors)`.
- `InstancePool` (`instance_pool.py`) pre-computes per-scene slot metadata keyed by snapshot path. `VideoWorker._execute_task` acquires a slot, builds a fresh `MineDojoSim(generate_world_type="from_file", world_file_path=...)`, runs `OperationSequencer`, then releases the slot. `MineDojoSim` objects are NOT shared across processes — only slot metadata is.
- `VideoEncoder` (`video_encoder.py`) pipes raw RGB24 frames to an `ffmpeg` subprocess producing H.264 (`libx264`, CRF 23, `fast` preset) `.mp4` files.
- `task_dsl.py` exposes `TaskGenerator` for randomized movement/combat/mine/entity/craft batches.
- CLI: `python -m minedojo.workers.main --snapshots-dir --output-dir --n-workers [--image-width --image-height]`.

### World Snapshots (`minedojo/world_snapshots/`)

Pre-build 7 reusable Minecraft world saves so workers load them instantly via `FileWorldGenerator` instead of regenerating terrain each task.

`SCENE_CONFIGS` (`config.py`) is a dict of 7 `SceneConfig` dataclasses:

| Scene | `world_type` | Use case |
|-------|--------------|----------|
| `plains` | `specified_biome` (plains) | navigate, combat, mining |
| `forest` | `specified_biome` (forest) | navigate, chop_tree, craft |
| `extreme_hills` | `specified_biome` (extreme hills) | navigate (slopes), mining |
| `village` | `default` | trade, navigate, attack |
| `cave` | `flat` | navigate (dark), mining |
| `water` | `specified_biome` (ocean) | navigate (swim), spawn_entity |
| `gui_item` | `flat` | trade, enchant, brew, anvil, chest, craft |

Each config carries `biome`, `spawn_region` bbox, `default_inventory`, `operation_whitelist`, and an optional `extra_setup` hook. `SnapshotBuilder(scene_config, image_size).build(output_path)` constructs the `MineDojoSim`, runs the registered setup function (`setup_village`, `setup_cave`, `setup_gui_room` — registered via `@_register` into `_SETUP_FUNCTIONS`), sets time/weather, then calls `env.save_snapshot(output_path)`. `setup_cave` builds an 11×4×11 stone room; `setup_gui_room` places crafting table/furnace/enchanting table/anvil/brewing stand/double chest + 3 villagers.

### Key Files

| File | Purpose |
|------|---------|
| `minedojo/tasks/__init__.py` | Task registry, `make()` factory, YAML spec loading, variable substitution |
| `minedojo/sim/sim.py` | Core Gymnasium environment (`MineDojoSim`) |
| `minedojo/sim/handler.py` | Base Handler class with Jinja2 XML templating |
| `minedojo/sim/config_sim_spec.py` | Assembles handlers into a mission XML spec |
| `minedojo/sim/spaces.py` | MineRL-compatible action/observation space definitions |
| `minedojo/sim/bridge/bridge_env/bridge_env.py` | Pyro4 bridge to Java Malmo |
| `minedojo/sim/wrappers/ar_nn/` | ARNN wrapper stack (action discretization + masks + delta inventory) |
| `minedojo/sim/mc_meta/mc.py` | Minecraft constants (items, biomes, keymaps, crafting recipes) |
| `minedojo/sim/Malmo/VERSION` | Malmo mod version (currently `0.37.0`) |
| `minedojo/tasks/meta/base.py` | `MetaTaskBase` and `ExtraSpawnMetaTaskBase` — base classes for all tasks |
| `minedojo/tasks/description_files/*.yaml` | Task specifications (specs, prompts, guidance, benchmark suite) |
| `minedojo/operations/sequencer.py` | `OperationSequencer` — runs scripted operation sequences |
| `minedojo/operations/registry.py` | `OPERATION_REGISTRY` — string-name → operation-class map |
| `minedojo/pathfinding/navigator.py` | `Navigator.navigate_to` — A* entry point |
| `minedojo/workers/scheduler.py` | `TaskScheduler` — multi-process video generation orchestrator |
| `minedojo/world_snapshots/config.py` | `SCENE_CONFIGS` — 7 scene type definitions |
| `minedojo/world_snapshots/builder.py` | `SnapshotBuilder` — builds world saves for `FileWorldGenerator` |

### MineCLIP and Agent Code

The MineCLIP reward model and agent implementations live in a separate repository (`github.com/MineDojo/MineCLIP`), not in this codebase. This repository is the simulation framework and knowledge base data loaders only.
