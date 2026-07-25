#!/usr/bin/env python3
"""
Build all 7 world snapshots for MineDojo.

Usage:
    python scripts/build_snapshots.py --output /data/snapshots/
    python scripts/build_snapshots.py --output ./snapshots --image-size 160 256 --seed 42
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(
        description="Build MineDojo world snapshots for all 7 scenes."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory where snapshots will be saved.",
    )
    parser.add_argument(
        "--image-size",
        nargs=2,
        type=int,
        default=[160, 256],
        metavar=("WIDTH", "HEIGHT"),
        help="Observation image size (default: 160 256).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducibility.",
    )
    parser.add_argument(
        "--scene",
        type=str,
        nargs="*",
        default=None,
        help="Specific scene(s) to build (default: all).",
    )
    args = parser.parse_args()

    # Deferred imports — argparse handles --help before this point.
    from minedojo.world_snapshots.config import SCENE_CONFIGS
    from minedojo.world_snapshots.builder import SnapshotBuilder

    os.makedirs(args.output, exist_ok=True)

    scenes_to_build = (
        args.scene if args.scene else list(SCENE_CONFIGS.keys())
    )

    failed = []
    for scene_name in scenes_to_build:
        if scene_name not in SCENE_CONFIGS:
            print(f"Unknown scene: {scene_name}")
            failed.append(scene_name)
            continue

        config = SCENE_CONFIGS[scene_name]
        print(f"Building snapshot: {scene_name} ...")

        builder = SnapshotBuilder(
            scene_config=config,
            image_size=tuple(args.image_size),
            seed=args.seed,
        )

        output_path = os.path.join(args.output, scene_name)
        try:
            builder.build(output_path)
            print(f"  -> Saved to {output_path}")
        except Exception as e:
            print(f"  -> FAILED: {e}")
            failed.append(scene_name)

    if failed:
        print(f"\n{len(failed)} scene(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"\nAll {len(scenes_to_build)} snapshot(s) built successfully.")


if __name__ == "__main__":
    main()
