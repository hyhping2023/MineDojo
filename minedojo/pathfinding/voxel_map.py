"""
Incrementally constructed 3D occupancy grid from MineDojo voxel observations.

Uses a sparse dictionary (defaultdict) keyed by integer world coordinates (x, y, z).
Each cell stores: is_solid (bool), block_name (str), is_liquid (bool).
"""

from collections import defaultdict
from typing import Dict, Optional, Tuple

import numpy as np


class VoxelMap:
    """
    Incrementally built 3D occupancy grid from MineDojo voxel observations.

    The map uses a sparse representation via collections.defaultdict, keyed by
    integer (x, y, z) world coordinates. Each cell stores a dict with:
        - is_solid (bool): whether the block occupies its position
        - block_name (str): the Minecraft block name
        - is_liquid (bool): whether the block is a liquid (water, lava)

    Coordinates are in Minecraft conventions:
        X = east, Y = up, Z = south

    Args:
        xmin: Minimum local x offset from agent (inclusive), e.g., -3.
        xmax: Maximum local x offset from agent (inclusive), e.g., 3.
        ymin: Minimum local y offset from agent (inclusive), e.g., -1.
        ymax: Maximum local y offset from agent (inclusive), e.g., 5.
        zmin: Minimum local z offset from agent (inclusive), e.g., -3.
        zmax: Maximum local z offset from agent (inclusive), e.g., 3.
    """

    def __init__(
        self,
        xmin: int = -3,
        xmax: int = 3,
        ymin: int = -1,
        ymax: int = 5,
        zmin: int = -3,
        zmax: int = 3,
    ):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax

        # Sparse map: key=(x, y, z) int tuple, value=dict with is_solid, block_name, is_liquid
        self._map = defaultdict(
            lambda: {"is_solid": False, "block_name": "unknown", "is_liquid": False}
        )

    def update(self, obs_dict: dict) -> None:
        """
        Merge a new voxel observation into the global map.

        Reads ``obs_dict["voxels"]`` (a dict of 3D numpy arrays in Fortran order)
        and ``obs_dict["location_stats"]["pos"]`` (agent world position as [x, y, z])
        to convert local voxel coordinates to world block coordinates. Each cell
        in the voxel grid is upserted into the map.

        If ``obs_dict`` does not contain "voxels" or "location_stats", this is a
        no-op (e.g., environment was configured without voxels).

        Args:
            obs_dict: The observation dict returned by ``MineDojoSim.step()`` or
                      ``MineDojoSim.reset()``. Expected to contain ``"voxels"``
                      and ``"location_stats"`` keys.
        """
        if "voxels" not in obs_dict or "location_stats" not in obs_dict:
            return

        voxels = obs_dict["voxels"]
        location = obs_dict["location_stats"]

        # Agent world position (feet). numpy array [x, y, z] (float32).
        agent_pos = location.get("pos")
        if agent_pos is None or (isinstance(agent_pos, np.ndarray) and agent_pos.size < 3):
            return
        ax, ay, az = float(agent_pos[0]), float(agent_pos[1]), float(agent_pos[2])

        # Agent's block coordinate (floor of feet position).
        # This is the block the agent stands in (feet are inside this block).
        bx, by, bz = int(np.floor(ax)), int(np.floor(ay)), int(np.floor(az))

        # Voxel grid dimensions from the observation shape.
        # Shape is (nx, ny, nz) in Fortran (column-major) order.
        is_solid_arr = voxels.get("is_solid")
        if is_solid_arr is None:
            return

        nx, ny, nz = is_solid_arr.shape
        block_name_arr = voxels.get(
            "block_name",
            np.full((nx, ny, nz), "unknown", dtype=object),
        )
        is_liquid_arr = voxels.get(
            "is_liquid",
            np.full((nx, ny, nz), False, dtype=bool),
        )

        # Iterate all voxel cells. The array uses Fortran ordering:
        # index (ix, iy, iz) where ix varies fastest.
        for iz in range(nz):
            lz = self.zmin + iz  # local z offset from agent
            if lz > self.zmax:
                break
            wz = bz + lz  # world z coordinate

            for iy in range(ny):
                ly = self.ymin + iy
                if ly > self.ymax:
                    break
                wy = by + ly

                for ix in range(nx):
                    lx = self.xmin + ix
                    if lx > self.xmax:
                        break
                    wx = bx + lx

                    try:
                        solid = bool(is_solid_arr[ix, iy, iz])
                        liquid = bool(is_liquid_arr[ix, iy, iz])
                        name = str(block_name_arr[ix, iy, iz])
                    except IndexError:
                        continue

                    cell = self._map[(wx, wy, wz)]
                    cell["is_solid"] = solid
                    cell["block_name"] = name
                    cell["is_liquid"] = liquid

    def is_solid(self, x: int, y: int, z: int) -> bool:
        """
        Check if a block occupies position (x, y, z).

        Args:
            x, y, z: Integer world coordinates.

        Returns:
            True if the cell is known and solid, False otherwise (including
            unknown / out-of-bounds positions).
        """
        return self._map[(x, y, z)]["is_solid"]

    def is_liquid(self, x: int, y: int, z: int) -> bool:
        """
        Check if position (x, y, z) contains a liquid block (water or lava).

        Args:
            x, y, z: Integer world coordinates.

        Returns:
            True if the cell is known and liquid.
        """
        return self._map[(x, y, z)]["is_liquid"]

    def is_passable(self, x: int, y: int, z: int) -> bool:
        """
        Check if the agent can stand at block position (x, y, z).

        The agent requires:
            - A solid block at (x, y-1, z) for footing (the block to stand on),
              unless y <= 0 (void).
            - Both (x, y, z) and (x, y+1, z) must not be solid (no wall/head
              obstruction).

        Args:
            x, y, z: Integer world coordinates of the block the agent would
                     occupy with their feet.

        Returns:
            True if the position is passable/navigable.
        """
        # Need a solid block below as footing.
        # Allow void (y <= 0) to pass if no block below — simplifies edge cases
        # in maps that don't cover the very bottom of the world.
        if y > 0 and not self.is_solid(x, y - 1, z):
            return False

        # Agent occupies the block at feet level (y) and the block above (y+1).
        # Both must be empty.
        if self.is_solid(x, y, z) or self.is_solid(x, y + 1, z):
            return False

        return True

    def is_known(self, x: int, y: int, z: int) -> bool:
        """
        Check if position (x, y, z) has been observed (exists in the map).

        Args:
            x, y, z: Integer world coordinates.

        Returns:
            True if this position has been written to the map at least once.
        """
        # defaultdict creates entries on access, so we can't just check `in`.
        # We need to check if the key exists without creating one.
        return (x, y, z) in self._map

    def get_block_name(self, x: int, y: int, z: int) -> str:
        """
        Get the block name at position (x, y, z).

        Args:
            x, y, z: Integer world coordinates.

        Returns:
            The block name string, or ``"unknown"`` if not observed.
        """
        return self._map[(x, y, z)]["block_name"]

    def get_bounds(self) -> Optional[Dict[str, int]]:
        """
        Get the axis-aligned bounding box of the known map.

        Returns:
            A dict with keys ``"xmin"``, ``"xmax"``, ``"ymin"``, ``"ymax"``,
            ``"zmin"``, ``"zmax"`` giving the integer extents of observed cells.
            Returns ``None`` if the map is empty.
        """
        if not self._map:
            return None

        keys = list(self._map.keys())
        xs = [k[0] for k in keys]
        ys = [k[1] for k in keys]
        zs = [k[2] for k in keys]
        return {
            "xmin": min(xs),
            "xmax": max(xs),
            "ymin": min(ys),
            "ymax": max(ys),
            "zmin": min(zs),
            "zmax": max(zs),
        }

    @property
    def size(self) -> int:
        """Number of observed cells in the map."""
        return len(self._map)

    def __contains__(self, coord: Tuple[int, int, int]) -> bool:
        """Check if a coordinate has been observed."""
        return coord in self._map

    def __repr__(self) -> str:
        bounds = self.get_bounds()
        if bounds is None:
            return "VoxelMap(empty)"
        return (
            f"VoxelMap(cells={self.size}, "
            f"x=[{bounds['xmin']},{bounds['xmax']}], "
            f"y=[{bounds['ymin']},{bounds['ymax']}], "
            f"z=[{bounds['zmin']},{bounds['zmax']}])"
        )
