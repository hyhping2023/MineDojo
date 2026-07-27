"""Smoke test: generate one example video per world snapshot scene.

Submits a short, scene-appropriate task for each of the 7 scene types so you
can eyeball whether the pipeline (snapshot load -> MC launch -> frame capture
-> H.264 encode) is working end-to-end, and that the agent performs a visible
action (combat / entity spawn / inventory) rather than just turning.

Usage::

    python scripts/smoke_test_videos.py \\
        --snapshots-dir /data/snapshots \\
        --output-dir /data/videos_smoke \\
        --n-workers 4

Each scene produces one ``.mp4``. A summary table is printed at the end.
"""

import argparse
import logging
import sys
from pathlib import Path

from minedojo.world_snapshots.config import SCENE_CONFIGS
from minedojo.workers.task import VideoTask
from minedojo.workers.scheduler import TaskScheduler

logger = logging.getLogger(__name__)

# Per-scene voxel-free task sequences that produce visible, complete actions.
# navigate / mine_block / chop_tree require use_voxel=True (not enabled in the
# worker), so they're no-ops and avoided here. spawn_attack spawns a mob and
# fights it; spawn_entity spawns a mob to look at; open_inventory opens the
# inventory GUI.
SCENE_TASKS = {
    "plains": [
        ("spawn_attack", {"mob": "minecraft:zombie", "rel_pos": [5, 0, 0],
                          "weapon": "diamond_sword", "attack_steps": 30}),
    ],
    "forest": [
        ("spawn_attack", {"mob": "minecraft:zombie", "rel_pos": [5, 0, 0],
                          "weapon": "diamond_sword", "attack_steps": 30}),
    ],
    "extreme_hills": [
        ("spawn_attack", {"mob": "minecraft:skeleton", "rel_pos": [5, 0, 0],
                          "weapon": "iron_sword", "attack_steps": 30}),
    ],
    "village": [
        ("spawn_attack", {"mob": "minecraft:zombie", "rel_pos": [5, 0, 0],
                          "weapon": "diamond_sword", "attack_steps": 30}),
    ],
    "cave": [
        ("spawn_attack", {"mob": "minecraft:spider", "rel_pos": [4, 0, 0],
                          "weapon": "iron_sword", "attack_steps": 30}),
    ],
    "water": [
        ("spawn_entity", {"entity": "minecraft:squid", "rel_pos": [3, 0, 0]}),
        ("look_at", {"yaw": 90, "pitch": 0}),
        ("look_at", {"yaw": 0, "pitch": 0}),
    ],
    "gui_item": [
        ("open_inventory", {}),
        ("look_at", {"yaw": 90, "pitch": 0}),
        ("look_at", {"yaw": 0, "pitch": 0}),
    ],
}


def run_smoke_test(snapshots_dir, output_dir, n_workers=4, image_size=(480, 854)):
    scheduler = TaskScheduler(
        n_workers=n_workers,
        snapshots_dir=snapshots_dir,
        output_dir=output_dir,
        image_size=image_size,
    )
    scheduler.start()

    scene_types = list(SCENE_CONFIGS.keys())
    for scene_type in scene_types:
        operations = SCENE_TASKS.get(scene_type, [("open_inventory", {})])
        scheduler.submit(VideoTask(
            task_id=f"smoke_{scene_type}",
            scene_type=scene_type,
            operations=operations,
            max_steps=400,
            metadata={"smoke": True, "scene": scene_type},
        ))

    results = scheduler.collect_results(len(scene_types))
    scheduler.shutdown()
    return results


def main():
    parser = argparse.ArgumentParser(description="MineDojo smoke test: one video per scene")
    parser.add_argument("--snapshots-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--n-workers", type=int, default=4)
    # MineDojoSim treats image_size as (height, width); POVObservation sets
    # video_height=image_size[0], video_width=image_size[1]. Default 480p.
    parser.add_argument("--image-height", type=int, default=480,
                        help="POV frame height in pixels (default 480 = 480p)")
    parser.add_argument("--image-width", type=int, default=854,
                        help="POV frame width in pixels (default 854 = 16:9 480p)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    snapshots = Path(args.snapshots_dir)
    if not snapshots.exists():
        logger.error("Snapshots directory does not exist: %s", snapshots)
        sys.exit(1)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    logger.info("Smoke test: 1 video per scene, %d scenes, %d workers",
                len(SCENE_CONFIGS), args.n_workers)

    results = run_smoke_test(
        snapshots_dir=str(snapshots),
        output_dir=str(output),
        n_workers=args.n_workers,
        image_size=(args.image_height, args.image_width),
    )

    print()
    print("=" * 70)
    print("SMOKE TEST RESULTS")
    print("=" * 70)
    succeeded = 0
    for r in results:
        status = "OK  " if r.success else "FAIL"
        if r.success:
            succeeded += 1
        print(f"  [{status}] {r.task_id:28s} frames={r.frames:5d} "
              f"time={r.duration_seconds:6.1f}s path={r.video_path}")
        for err in r.errors:
            if err:
                print(f"         error: {err.strip().splitlines()[-1]}")
    print("=" * 70)
    print(f"Total: {len(results)} scenes, {succeeded} ok, {len(results) - succeeded} failed")
    print("=" * 70)
    sys.exit(0 if succeeded == len(results) else 1)


if __name__ == "__main__":
    main()
