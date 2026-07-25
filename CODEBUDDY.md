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
```

There are no tests, linters, or CI configuration in this repository. `pytest` is listed in `requirements.txt` but no test files exist.

## Architecture

MineDojo is a Gym-style Minecraft simulation framework for embodied agent research. Python >= 3.9, tested on Ubuntu 20.04 and macOS.

### Entry Point

`minedojo/__init__.py` exports `make` from `minedojo/tasks/__init__.py`. Users call:

```python
import minedojo
env = minedojo.make(task_id="combat_spider_plains_leather_armors_diamond_sword_shield", image_size=(160, 256))
```

### Layer Stack (top to bottom)

```
minedojo.make() → ARNNWrapper → MetaTaskBase (or MineDojoSim) → FastResetWrapper? → MineDojoSim → BridgeEnv → Malmo (Java)
```

1. **Task Layer** (`minedojo/tasks/`) — Task definitions, prompts, guidance, reward/success logic.
2. **Wrapper Layer** (`minedojo/sim/wrappers/`) — ARNNWrapper (camera discretization + action masks + delta inventory obs). FastResetWrapper for `/kill`-based resets.
3. **Simulation Layer** (`minedojo/sim/`) — MineDojoSim (extends `gym.Env`), configures handlers, delegates to BridgeEnv.
4. **Bridge Layer** (`minedojo/sim/bridge/`) — Pyro4 RPC between Python and the Java Minecraft Malmo mod.
5. **Malmo Mod** (`minedojo/sim/Malmo/`) — Vendored Java Minecraft Forge mod (subrepo of `cmu-rl/Malmo`, branch `minerl`, v0.37.0). Compiled via Gradle.

### Task System (`minedojo/tasks/`)

`minedojo/tasks/__init__.py` is the central registry (~500 lines). It:
- Loads YAML task specs from `description_files/` using OmegaConf
- Performs variable substitution to generate 1000s of programmatic tasks (biomes, mobs, materials, etc.)
- Supports three task families plus meta tasks:

| Task Type | Class | File |
|-----------|-------|------|
| Harvest | `HarvestMeta` | `meta/harvest.py` |
| Combat | `CombatMeta` | `meta/combat.py` |
| TechTree | `TechTreeMeta` | `meta/tech_tree.py` |
| Survival | `SurvivalMeta` | `meta/survival.py` |
| Creative | `CreativeMeta` | `meta/creative.py` |
| Playthrough | `Playthrough` | `meta/playthrough.py` |
| Open-Ended | `MineDojoSim` (raw) | `sim/sim.py` |

All meta tasks extend `MetaTaskBase` (or `ExtraSpawnMetaTaskBase`), which extends `gym.Wrapper` and wraps `MineDojoSim`. MetaTaskBase adds reward computation, success criteria checking, prompt/guidance management, and optional fast reset.

Every environment returned by `make()` is wrapped in `ARNNWrapper` (from `minedojo/sim/wrappers/ar_nn/`) which:
- Discretizes continuous camera actions
- Converts the multi-discrete action space to a flat categorical space for neural networks
- Provides action masks for invalid actions
- Computes delta inventory observations

### Simulation (`minedojo/sim/`)

**MineDojoSim** (`sim.py`) extends `gym.Env`. It:
- Assembles observation handlers, action handlers, world generator handlers, and server handlers
- Serializes the configuration to a Malmo mission XML via `ConfigSimSpec.to_xml()`
- Delegates environment stepping to `BridgeEnv`
- Provides Minecraft command wrappers: `spawn_mobs()`, `set_block()`, `teleport_agent()`, `set_inventory()`, `set_time()`, `set_weather()`, `random_teleport()`, etc.

**Handler system** (`handlers/`) — All handlers extend `Handler` (in `handler.py`) which uses Jinja2 templates for XML generation. Handlers are organized into:
- `handlers/agent/observations/` — POV, inventory, equipment, life stats, location, voxels, lidar, damage source, achievements, nearby tools
- `handlers/agent/actions/` — Camera, craft, smelt, equip, place, keyboard commands, swap slot
- `handlers/server/` — World generation, initial conditions, quit conditions, navigation

**Bridge** (`bridge/`) — `BridgeEnv` manages the Python-Java connection via Pyro4. `MCInstance` manages the Minecraft process lifecycle (launch, monitor via watchdog, cleanup). Socket communication is handled by `socket_comm.py`.

**Malmo mod** (`Malmo/`) — Java source at `Malmo/Minecraft/src/main/java/com/microsoft/Malmo/`. Key packages: `Client/` (Java-side Pyro4 client), `MissionHandlers/` (Java-side handler implementations), `Mixins/` (vanilla Minecraft bytecode patches), `Server/`, `Utils/`. The mod is launched via `launch_minecraft_in_background.py`.

### Data Module (`minedojo/data/`)

Knowledge base dataset loaders: `RedditDataset`, `WikiDataset`, `YouTubeDataset`. These fetch the internet-scale knowledge base (730K YouTube videos, 7K Wiki pages, 340K Reddit posts) used for training MineCLIP (in the separate MineCLIP repo).

### Key Files

| File | Purpose |
|------|---------|
| `minedojo/tasks/__init__.py` | Task registry, `make()` factory, YAML spec loading, variable substitution |
| `minedojo/sim/sim.py` | Core Gym environment (`MineDojoSim`) |
| `minedojo/sim/handler.py` | Base Handler class with Jinja2 XML templating |
| `minedojo/sim/config_sim_spec.py` | Assembles handlers into a mission XML spec |
| `minedojo/sim/spaces.py` | MineRL-compatible action/observation space definitions |
| `minedojo/sim/bridge/bridge_env/bridge_env.py` | Pyro4 bridge to Java Malmo |
| `minedojo/sim/wrappers/ar_nn/` | ARNN wrapper stack (action discretization + masks + delta inventory) |
| `minedojo/sim/mc_meta/mc.py` | Minecraft constants (items, biomes, keymaps, crafting recipes) |
| `minedojo/tasks/meta/base.py` | `MetaTaskBase` and `ExtraSpawnMetaTaskBase` — base classes for all tasks |
| `minedojo/tasks/description_files/*.yaml` | Task specifications (specs, prompts, guidance, benchmark suite) |

### MineCLIP and Agent Code

The MineCLIP reward model and agent implementations live in a separate repository (`github.com/MineDojo/MineCLIP`), not in this codebase. This repository is the simulation framework and knowledge base data loaders only.
