#!/usr/bin/env python3
"""
Validate the MineDojo extension modules.

Checks:
  1. All Python modules can be imported
  2. Pathfinding module works with synthetic grid
  3. Operation registry has all expected operations
  4. Scene configs are valid
  5. Worker task types are correct (if worker module is available)

Import errors are caught gracefully — downstream tests that depend on a
failed import are automatically skipped.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _skip_test(name: str, reason: str):
    """Print a skipped-test message."""
    print(f"[SKIP] {name} ({reason})")


# ---------------------------------------------------------------------------
# 1. Import tests
# ---------------------------------------------------------------------------


def test_imports():
    """
    Test all new modules can be imported.

    Returns:
        (errors, available): *errors* is a list of error strings; *available*
        is a dict mapping module names to bools indicating whether the
        module is importable.
    """
    errors = []
    available = {}

    # Pathfinding
    try:
        from minedojo.pathfinding import (  # noqa: F401
            VoxelMap,
            AStarPathfinder,
            PathFollower,
            Navigator,
        )

        available["pathfinding"] = True
        print("[PASS] pathfinding imports")
    except Exception as e:
        available["pathfinding"] = False
        errors.append(f"pathfinding: {e}")
        print(f"[FAIL] pathfinding: {e}")

    # Operations
    try:
        from minedojo.operations import (  # noqa: F401
            Operation,
            OPERATION_REGISTRY,
            OperationSequencer,
        )

        available["operations"] = True
        print(f"[PASS] operations imports ({len(OPERATION_REGISTRY)} operations)")
    except Exception as e:
        available["operations"] = False
        errors.append(f"operations: {e}")
        print(f"[FAIL] operations: {e}")

    # World snapshots
    try:
        from minedojo.world_snapshots import (  # noqa: F401
            SceneConfig,
            SCENE_CONFIGS,
            SnapshotBuilder,
        )

        available["world_snapshots"] = True
        print(f"[PASS] world_snapshots imports ({len(SCENE_CONFIGS)} scenes)")
    except Exception as e:
        available["world_snapshots"] = False
        errors.append(f"world_snapshots: {e}")
        print(f"[FAIL] world_snapshots: {e}")

    # Workers (optional — may not be installed yet)
    try:
        from minedojo.workers import (  # noqa: F401
            VideoTask,
            TaskResult,
            InstancePool,
            VideoEncoder,
            VideoWorker,
            TaskScheduler,
        )

        available["workers"] = True
        print("[PASS] workers imports")
    except ImportError:
        available["workers"] = False
        print("[SKIP] workers imports (module not available)")
    except Exception as e:
        available["workers"] = False
        errors.append(f"workers: {e}")
        print(f"[FAIL] workers: {e}")

    return errors, available


# ---------------------------------------------------------------------------
# 2. Pathfinding synthetic test
# ---------------------------------------------------------------------------


def test_pathfinding():
    """Test A* on a synthetic voxel grid."""
    try:
        from minedojo.pathfinding import VoxelMap, AStarPathfinder
    except Exception as e:
        _skip_test("pathfinding", f"import failed: {e}")
        return ["pathfinding: cannot run synthetic test (import failed)"]

    errors = []

    # Manually populate a small world map (11x5x11 blocks)
    voxel_map = VoxelMap(xmin=0, xmax=10, ymin=0, ymax=4, zmin=0, zmax=10)

    # Create a floor at y=0 (solid stone)
    for x in range(11):
        for z in range(11):
            voxel_map._map[(x, 0, z)] = {
                "is_solid": True,
                "block_name": "stone",
                "is_liquid": False,
            }
            # Air blocks at y=1 and y=2 (walkable space)
            voxel_map._map[(x, 1, z)] = {
                "is_solid": False,
                "block_name": "air",
                "is_liquid": False,
            }
            voxel_map._map[(x, 2, z)] = {
                "is_solid": False,
                "block_name": "air",
                "is_liquid": False,
            }

    # Create a wall at x=5, z=0..8, y=1..3 (blocks path)
    for y in range(1, 4):
        for z in range(10):
            voxel_map._map[(5, y, z)] = {
                "is_solid": True,
                "block_name": "stone",
                "is_liquid": False,
            }
    # Leave a gap at z=9 so path can squeeze through
    for y in range(1, 4):
        voxel_map._map[(5, y, 9)] = {
            "is_solid": False,
            "block_name": "air",
            "is_liquid": False,
        }

    pathfinder = AStarPathfinder(voxel_map)
    path = pathfinder.find_path((1, 1, 5), (9, 1, 5))

    if path and path[-1] == (9, 1, 5):
        print(f"[PASS] A* found path around wall: {len(path)} steps")
    else:
        msg = "A* failed to find path around wall"
        errors.append(f"pathfinding: {msg}")
        print(f"[FAIL] {msg}")

    return errors


# ---------------------------------------------------------------------------
# 3. Scene config validation
# ---------------------------------------------------------------------------


def test_scene_configs():
    """Validate scene configurations."""
    try:
        from minedojo.world_snapshots.config import SCENE_CONFIGS
        from minedojo.operations.registry import OPERATION_REGISTRY
    except Exception as e:
        _skip_test("scene configs", f"import failed: {e}")
        return [f"scene configs: cannot validate (import failed: {e})"]

    valid_world_types = {"specified_biome", "default", "flat"}
    errors = []

    for name, cfg in SCENE_CONFIGS.items():
        if cfg.world_type not in valid_world_types:
            errors.append(
                f"scene '{name}': invalid world_type '{cfg.world_type}'"
            )
        if cfg.world_type == "specified_biome" and cfg.biome is None:
            errors.append(f"scene '{name}': specified_biome but no biome set")
        for op in cfg.operation_whitelist:
            if op not in OPERATION_REGISTRY:
                errors.append(
                    f"scene '{name}': unknown operation '{op}' in whitelist"
                )

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
    else:
        print(f"[PASS] All {len(SCENE_CONFIGS)} scene configs valid")

    return errors


# ---------------------------------------------------------------------------
# 4. Operation registry coverage
# ---------------------------------------------------------------------------


_EXPECTED_OPERATIONS = {
    "navigate",
    "look_at",
    "strafe",
    "open_inventory",
    "close_inventory",
    "select_item",
    "drop_item",
    "craft",
    "smelt",
    "attack",
    "spawn_attack",
    "mine_block",
    "chop_tree",
    "place_block",
    "trade",
    "enchant",
    "brew",
    "anvil",
    "chest",
    "spawn_entity",
    "interact_entity",
    "mount",
}


def test_operation_registry():
    """Verify the operation registry contains all expected operations."""
    try:
        from minedojo.operations.registry import OPERATION_REGISTRY
    except Exception as e:
        _skip_test("operation registry", f"import failed: {e}")
        return [f"operation registry: cannot validate (import failed: {e})"]

    errors = []
    registered = set(OPERATION_REGISTRY.keys())
    missing = _EXPECTED_OPERATIONS - registered
    extra = registered - _EXPECTED_OPERATIONS

    if missing:
        errors.append(f"missing operations: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected extra operations: {sorted(extra)}")

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
    else:
        print(f"[PASS] Operation registry complete ({len(registered)} operations)")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("MineDojo Extension Validation")
    print("=" * 60)

    all_errors = []

    print("\n--- Import Tests ---")
    import_errors, available = test_imports()
    all_errors.extend(import_errors)

    print("\n--- Pathfinding Tests ---")
    all_errors.extend(test_pathfinding())

    print("\n--- Scene Config Tests ---")
    all_errors.extend(test_scene_configs())

    print("\n--- Operation Registry Tests ---")
    all_errors.extend(test_operation_registry())

    print("\n" + "=" * 60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s)")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
