"""Entry-point script for the MineDojo Parallel Video Generator.

Usage::

    python -m minedojo.workers.main \\
        --snapshots-dir /path/to/snapshots \\
        --output-dir /path/to/output \\
        --n-workers 4

Or import and run programmatically::

    from minedojo.workers.main import run_default_pipeline
    run_default_pipeline(
        snapshots_dir="/path/to/snapshots",
        output_dir="/path/to/output",
        n_workers=4,
    )
"""

import argparse
import logging
import sys
from pathlib import Path

from minedojo.world_snapshots.config import SCENE_CONFIGS
from minedojo.workers.task import VideoTask
from minedojo.workers.scheduler import TaskScheduler

logger = logging.getLogger(__name__)


def run_default_pipeline(
    snapshots_dir: str,
    output_dir: str,
    n_workers: int = 4,
    image_size: tuple = (160, 256),
) -> list:
    """Run a default pipeline: one movement task per scene type.

    This is a convenience entry point for testing / quick validation
    that the pipeline is functioning correctly.

    Parameters:
        snapshots_dir: Directory with pre-built world snapshots.
        output_dir: Directory for video output.
        n_workers: Number of worker processes.
        image_size: ``(width, height)`` observation size.

    Returns:
        List of :class:`~minedojo.workers.task.TaskResult` objects.
    """
    scheduler = TaskScheduler(
        n_workers=n_workers,
        snapshots_dir=snapshots_dir,
        output_dir=output_dir,
        image_size=image_size,
    )
    scheduler.start()

    # Submit one basic movement task per scene type for smoke testing
    scene_types = list(SCENE_CONFIGS.keys())
    for scene_type in scene_types:
        task = VideoTask(
            task_id=f"test_{scene_type}",
            scene_type=scene_type,
            operations=[("navigate", {"target": [10, 63, 0], "max_steps": 100})],
            metadata={"test": True, "scene": scene_type},
        )
        scheduler.submit(task)

    results = scheduler.collect_results(len(scene_types))
    scheduler.shutdown()

    return results


def main():
    """CLI entry point for the parallel video generator."""
    parser = argparse.ArgumentParser(
        description="MineDojo Parallel Video Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python -m minedojo.workers.main \\
      --snapshots-dir ./snapshots \\
      --output-dir ./videos \\
      --n-workers 4
        """,
    )
    parser.add_argument(
        "--snapshots-dir", required=True,
        help="Path to directory with pre-built world snapshots."
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Path to directory for generated video files."
    )
    parser.add_argument(
        "--n-workers", type=int, default=4,
        help="Number of worker processes (default: 4)."
    )
    parser.add_argument(
        "--image-width", type=int, default=160,
        help="Observation image width (default: 160)."
    )
    parser.add_argument(
        "--image-height", type=int, default=256,
        help="Observation image height (default: 256)."
    )
    parser.add_argument(
        "--task-spec", default=None,
        help="JSON file with custom task specification (not yet implemented)."
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    # Validate paths
    snapshots = Path(args.snapshots_dir)
    if not snapshots.exists():
        logger.error("Snapshots directory does not exist: %s", snapshots)
        sys.exit(1)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    image_size = (args.image_width, args.image_height)

    logger.info("Starting parallel video generation pipeline ...")
    logger.info("  Snapshots dir: %s", snapshots)
    logger.info("  Output dir:    %s", output)
    logger.info("  Workers:       %d", args.n_workers)
    logger.info("  Image size:    %s", image_size)

    results = run_default_pipeline(
        snapshots_dir=str(snapshots),
        output_dir=str(output),
        n_workers=args.n_workers,
        image_size=image_size,
    )

    # Print summary
    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    succeeded = 0
    for r in results:
        status = "OK" if r.success else "FAIL"
        if r.success:
            succeeded += 1
        print(
            f"  [{status}] {r.task_id:40s}  "
            f"frames={r.frames:6d}  "
            f"time={r.duration_seconds:6.1f}s  "
            f"path={r.video_path}"
        )
        for err in r.errors:
            if err:
                print(f"         Error: {err}")
    print("=" * 60)
    print(f"Total: {len(results)} tasks, {succeeded} succeeded, "
          f"{len(results) - succeeded} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
