"""
Pathfinding module for MineDojo.

Provides 3D voxel map building, A* pathfinding on the voxel grid,
path following via Minecraft actions, and a high-level navigator.

Exports:
    VoxelMap: Incrementally constructed 3D occupancy grid from voxel observations.
    AStarPathfinder: A* search on the 3D voxel grid.
    PathFollower: Converts waypoint paths to Minecraft actions.
    Navigator: High-level interface combining mapping, pathfinding, and control.
"""

from .voxel_map import VoxelMap
from .astar import AStarPathfinder
from .controller import PathFollower
from .navigator import Navigator

__all__ = ["VoxelMap", "AStarPathfinder", "PathFollower", "Navigator"]
