"""
A* pathfinder on a 3D voxel occupancy grid.

Supports straight, diagonal, jump-up, step-down, and falling moves with
configurable costs. Avoids water traversal unless the goal is in water.
"""

import heapq
import math
from typing import List, Optional, Tuple

from .voxel_map import VoxelMap

# Pre-computed direction vectors (dx, dz) for *player-facing* coordinates.
# Minecraft convention: X=east (+x), Z=south (+z).
_STRAIGHT_DIRS = [
    (1, 0),   # east
    (-1, 0),  # west
    (0, 1),   # south
    (0, -1),  # north
]

_DIAGONAL_DIRS = [
    (1, 1),   # south-east
    (1, -1),  # north-east
    (-1, 1),  # south-west
    (-1, -1), # north-west
]

# For diagonal moves, the two adjacent straight cells that must also be passable.
_DIAGONAL_ADJACENT = {
    (1, 1):   [(1, 0), (0, 1)],
    (1, -1):  [(1, 0), (0, -1)],
    (-1, 1):  [(-1, 0), (0, 1)],
    (-1, -1): [(-1, 0), (0, -1)],
}


class AStarPathfinder:
    """
    A* search on a 3D voxel grid provided by a :class:`VoxelMap`.

    The search explores a neighborhood that includes:
        - 4 straight horizontal moves (same Y level)
        - 4 diagonal horizontal moves (only if both adjacent straights are passable)
        - Jump up (+1 Y): requires landing passable, clearance at y+2
        - Step down (-1 Y): requires landing passable
        - Fall (-2 to -3 Y): no special requirement (safe fall)

    Water (liquid) cells are avoided unless the goal itself is in water.

    Args:
        voxel_map: The :class:`VoxelMap` instance providing passability checks.
        max_iterations: Maximum number of search iterations to prevent infinite
                        loops on impossible paths.  Default 10000.
    """

    def __init__(self, voxel_map: VoxelMap, max_iterations: int = 10000):
        self.voxel_map = voxel_map
        self.max_iterations = max_iterations

        # Movement costs
        self.cost_straight = 1.0
        self.cost_diagonal = 1.414
        self.cost_jump = 2.0       # jumping up costs more
        self.cost_step_down = 1.0
        self.cost_fall = 1.0
        self.cost_water = 4.0      # water traversal avoided unless goal is in water

    def find_path(
        self,
        start: Tuple[int, int, int],
        goal: Tuple[int, int, int],
    ) -> Optional[List[Tuple[int, int, int]]]:
        """
        Find a path from start to goal using A* on the 3D voxel grid.

        Args:
            start: (x, y, z) integer world coordinates of the starting position.
            goal: (x, y, z) integer world coordinates of the target position.

        Returns:
            A list of (x, y, z) waypoints from start to goal (inclusive), or
            ``None`` if no path exists or the search limit is exceeded.
        """
        if start == goal:
            return [start]

        # Check if goal area is in water (used for cost penalty).
        is_goal_in_water = self._is_position_in_water(goal)

        # A* state
        open_set = []  # priority queue: (f_score, tiebreaker, pos)
        tiebreaker = 0

        # g_score: cost from start to this node
        g_score = {start: 0.0}
        # f_score = g_score + heuristic
        f_score = {start: self._heuristic(start, goal)}

        # came_from: node -> predecessor
        came_from = {}

        heapq.heappush(open_set, (f_score[start], tiebreaker, start))
        tiebreaker += 1

        # Set of visited nodes for quick lookup
        closed_set = set()

        iterations = 0

        while open_set and iterations < self.max_iterations:
            iterations += 1

            _, _, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            if current == goal:
                return self._reconstruct_path(came_from, current)

            closed_set.add(current)

            for neighbor, cost in self._get_neighbors(current, is_goal_in_water):
                if neighbor in closed_set:
                    continue

                tentative_g = g_score[current] + cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], tiebreaker, neighbor))
                    tiebreaker += 1

        return None  # No path found

    def _get_neighbors(self, pos, is_goal_in_water):
        """
        Generate valid neighbors for a given position.

        Args:
            pos: (x, y, z) tuple.
            is_goal_in_water: bool indicating whether the goal is in water,
                              which relaxes water avoidance.

        Yields:
            Tuples of ((nx, ny, nz), cost) for each valid neighbor.
        """
        x, y, z = pos

        # 1. Straight horizontal moves (same Y)
        for dx, dz in _STRAIGHT_DIRS:
            nx, nz = x + dx, z + dz
            if self.voxel_map.is_passable(nx, y, nz):
                cost = self.cost_straight
                if not is_goal_in_water and self._is_position_in_water((nx, y, nz)):
                    cost = self.cost_water
                yield (nx, y, nz), cost

        # 2. Diagonal horizontal moves (only if both adjacent straights passable)
        for (dx, dz), adj_dirs in _DIAGONAL_ADJACENT.items():
            nx, nz = x + dx, z + dz

            # Check diagonal corner is passable
            if not self.voxel_map.is_passable(nx, y, nz):
                continue

            # Check both adjacent straight cells are passable
            adj_passable = True
            for adx, adz in adj_dirs:
                if not self.voxel_map.is_passable(x + adx, y, z + adz):
                    adj_passable = False
                    break
            if not adj_passable:
                continue

            cost = self.cost_diagonal
            if not is_goal_in_water and self._is_position_in_water((nx, y, nz)):
                cost = self.cost_water
            yield (nx, y, nz), cost

        # 3. Jump up (+1 Y): land on a block 1 higher.
        # Requires: landing spot passable at (x, y+1, z) AND clearance at (x, y+2, z)
        ny_up = y + 1
        if (
            self.voxel_map.is_passable(x, ny_up, z)
            and not self.voxel_map.is_solid(x, ny_up + 1, z)
        ):
            cost = self.cost_jump
            if not is_goal_in_water and self._is_position_in_water((x, ny_up, z)):
                cost = self.cost_water
            yield (x, ny_up, z), cost

        # 3b. Forward jump (+1 XZ and +1 Y): jump onto a block 1 higher
        # while moving forward. Only attempted for straight directions.
        for dx, dz in _STRAIGHT_DIRS:
            nx, nz = x + dx, z + dz
            nj_y = y + 1
            if (
                self.voxel_map.is_passable(nx, nj_y, nz)
                and not self.voxel_map.is_solid(nx, nj_y + 1, nz)
            ):
                cost = self.cost_jump
                if not is_goal_in_water and self._is_position_in_water(
                    (nx, nj_y, nz)
                ):
                    cost = self.cost_water
                yield (nx, nj_y, nz), cost

        # 4. Step down (-1 Y): step down 1 block. Requires landing passable.
        ny_down = y - 1
        if self.voxel_map.is_passable(x, ny_down, z):
            yield (x, ny_down, z), self.cost_step_down

        # 5. Fall (-2 to -3 Y): no special requirement (safe fall).
        for drop in range(2, 4):  # drop 2 or 3 blocks
            ny_fall = y - drop
            if ny_fall >= 0 and self.voxel_map.is_passable(x, ny_fall, z):
                yield (x, ny_fall, z), self.cost_fall

    def _is_position_in_water(self, pos: Tuple[int, int, int]) -> bool:
        """Check if a position is in water (liquid at feet level or head level)."""
        x, y, z = pos
        return self.voxel_map.is_liquid(x, y, z) or self.voxel_map.is_liquid(
            x, y + 1, z
        )

    @staticmethod
    def _heuristic(
        a: Tuple[int, int, int],
        b: Tuple[int, int, int],
    ) -> float:
        """
        Manhattan 3D distance heuristic.

        Simple and admissible on the Minecraft grid (each step changes
        at most one coordinate by 1 in absolute value, or at most dx+dy+dz
        total). The heuristic is consistent (monotone) as well, which
        guarantees optimality with A* on a grid.
        """
        return float(abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]))

    @staticmethod
    def _reconstruct_path(
        came_from: dict,
        current: Tuple[int, int, int],
    ) -> List[Tuple[int, int, int]]:
        """Reconstruct the path from start to goal by following predecessors."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
