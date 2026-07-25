"""World Snapshots module for MineDojo.

Provides scene configurations and a builder for creating pre-configured
Minecraft world snapshots used in agent training and evaluation.
"""

from minedojo.world_snapshots.config import SceneConfig, SCENE_CONFIGS
from minedojo.world_snapshots.builder import SnapshotBuilder

__all__ = [
    "SceneConfig",
    "SCENE_CONFIGS",
    "SnapshotBuilder",
]
