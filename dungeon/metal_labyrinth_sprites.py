from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Tuple

from .sprite import Sprite

class MetalTile(IntEnum):
    """
    Tile types for the metal labyrinth tile set.

    These are separate from dungeon_gen.Tile because the metal labyrinth
    has different tile semantics (e.g., north walls require base tiles below).
    """

    NOTHING = 0

    # Walkable tiles
    FLOOR = 1
    NORTH_WALL_BASE = 2  # Shadow row below north walls (walkable)
    PILLAR_BASE = 3  # Base below pillars (walkable)
    CONVEX_SE_BASE = 4  # Base below convex SE corner (walkable)
    CONVEX_SW_BASE = 5  # Base below convex SW corner (walkable)

    # Walls (non-walkable)
    NORTH_WALL = 10
    SOUTH_WALL = 11
    WEST_WALL = 12
    EAST_WALL = 13

    # Corners (non-walkable)
    NW_CORNER = 20
    NE_CORNER = 21
    SW_CORNER = 22
    SE_CORNER = 23

    # Convex corners for interior cutouts (non-walkable)
    CONVEX_NW = 30
    CONVEX_NE = 31
    CONVEX_SW = 32
    CONVEX_SE = 33

    # Pillar (non-walkable)
    PILLAR = 40

    # Doors (walkable, used for room navigation)
    # These render as floor but are tracked for pathfinding
    NORTH_DOOR_WEST = 50
    NORTH_DOOR_EAST = 51
    SOUTH_DOOR_WEST = 52
    SOUTH_DOOR_EAST = 53
    WEST_DOOR_NORTH = 54
    WEST_DOOR_SOUTH = 55
    EAST_DOOR_NORTH = 56
    EAST_DOOR_SOUTH = 57


# ASCII Art Dialect for Metal Labyrinth Rooms
# ============================================
#
# This dialect supports the metal labyrinth tile set where:
# - North walls/corners need a "base" tile directly below them (walkable shadow)
# - Pillars need a "base" tile directly below them
# - Convex NW/NE corners need base tiles below them
# - Doors are navigational markers that render as floor
#
# Characters:
#   Corners (non-walkable):
#     1 = NW corner
#     2 = NE corner
#     3 = SW corner
#     4 = SE corner
#
#   Walls (non-walkable):
#     - = north wall
#     _ = south wall
#     [ = west wall
#     ] = east wall
#
#   Walkable floor tiles:
#     . = regular floor
#     , = north wall base (shadow row below north walls/corners)
#     ; = pillar base
#     < = convex SW base
#     > = convex SE base
#
#   Convex corners for interior cutouts (non-walkable):
#     ^ = convex NW
#     ! = convex NE
#     ~ = convex SW (requires < directly below)
#     ` = convex SE (requires > directly below)
#
#   Pillars (non-walkable):
#     P = pillar (requires ; directly below)
#
#   Doors (walkable, used for room navigation):
#     n = north door west half
#     N = north door east half
#     s = south door west half
#     S = south door east half
#     w = west door north half
#     W = west door south half
#     e = east door north half
#     E = east door east half
#
#   Void:
#     (space) = nothing/void outside the room
#
# Example room:
#
#   1----nN----2
#   [,,,,,,,,,,]
#   [..........]
#   [..........]
#   w..........e
#   W..........E
#   [..........]
#   [..........]
#   [..........]
#   3____sS____4
#
# The second row uses ',' (north wall base) because it's directly below
# the north wall row. This is the shadow/gradient area that's walkable.


METAL_ASCII_TO_TILE: Dict[str, MetalTile] = {
    " ": MetalTile.NOTHING,
    # Corners
    "1": MetalTile.NW_CORNER,
    "2": MetalTile.NE_CORNER,
    "3": MetalTile.SW_CORNER,
    "4": MetalTile.SE_CORNER,
    # Walls
    "-": MetalTile.NORTH_WALL,
    "_": MetalTile.SOUTH_WALL,
    "[": MetalTile.WEST_WALL,
    "]": MetalTile.EAST_WALL,
    # Floor tiles
    ".": MetalTile.FLOOR,
    ",": MetalTile.NORTH_WALL_BASE,
    ";": MetalTile.PILLAR_BASE,
    "<": MetalTile.CONVEX_SW_BASE,
    ">": MetalTile.CONVEX_SE_BASE,
    # Convex corners
    "^": MetalTile.CONVEX_NW,
    "!": MetalTile.CONVEX_NE,
    "~": MetalTile.CONVEX_SW,
    "`": MetalTile.CONVEX_SE,
    # Pillar
    "P": MetalTile.PILLAR,
    # Doors
    # Door tiles will rended the same as FLOOR tiles
    # but can be identified as room boundaries by strategy
    "n": MetalTile.NORTH_DOOR_WEST,
    "N": MetalTile.NORTH_DOOR_EAST,
    "s": MetalTile.SOUTH_DOOR_WEST,
    "S": MetalTile.SOUTH_DOOR_EAST,
    "w": MetalTile.WEST_DOOR_NORTH,
    "W": MetalTile.WEST_DOOR_SOUTH,
    "e": MetalTile.EAST_DOOR_NORTH,
    "E": MetalTile.EAST_DOOR_SOUTH,
}

# Tiles that require a specific "base" tile directly below them
TILES_REQUIRING_BASE: Dict[MetalTile, MetalTile] = {
    MetalTile.NORTH_WALL: MetalTile.NORTH_WALL_BASE,
    MetalTile.NW_CORNER: MetalTile.NORTH_WALL_BASE,
    MetalTile.NE_CORNER: MetalTile.NORTH_WALL_BASE,
    MetalTile.PILLAR: MetalTile.PILLAR_BASE,
    MetalTile.CONVEX_SW: MetalTile.CONVEX_SW_BASE,
    MetalTile.CONVEX_SE: MetalTile.CONVEX_SE_BASE,
}

# Base tiles and the tiles that should be directly above them
# This is used to detect orphaned base tiles
# Note: NORTH_WALL_BASE can also be below CONVEX_SW/CONVEX_SE when they're
# part of the north wall row (adjacent to doors)
BASE_TILES_EXPECTED_ABOVE: Dict[MetalTile, set] = {
    MetalTile.NORTH_WALL_BASE: {
        MetalTile.NORTH_WALL, MetalTile.NW_CORNER, MetalTile.NE_CORNER,
        MetalTile.CONVEX_SW, MetalTile.CONVEX_SE,  # When part of north wall row
    },
    MetalTile.PILLAR_BASE: {MetalTile.PILLAR},
    MetalTile.CONVEX_SW_BASE: {MetalTile.CONVEX_SW},
    MetalTile.CONVEX_SE_BASE: {MetalTile.CONVEX_SE},
}

# Walkable tiles (for pathfinding/collision)
WALKABLE_TILES = {
    MetalTile.FLOOR,
    MetalTile.NORTH_WALL_BASE,
    MetalTile.PILLAR_BASE,
    MetalTile.CONVEX_SW_BASE,
    MetalTile.CONVEX_SE_BASE,
    MetalTile.NORTH_DOOR_WEST,
    MetalTile.NORTH_DOOR_EAST,
    MetalTile.SOUTH_DOOR_WEST,
    MetalTile.SOUTH_DOOR_EAST,
    MetalTile.WEST_DOOR_NORTH,
    MetalTile.WEST_DOOR_SOUTH,
    MetalTile.EAST_DOOR_NORTH,
    MetalTile.EAST_DOOR_SOUTH,
}

# Door slot characters (for detecting doors in templates)
METAL_DOOR_CHARS = {"n", "N", "s", "S", "w", "W", "e", "E"}


@dataclass
class ParseError:
    """Error found during ASCII art parsing."""

    row: int
    column: int
    message: str


import numpy as np


def check_valid_tiling(tiles: np.ndarray) -> List[ParseError]:
    """
    Check if a 2D tile array satisfies all tiling rules.

    Rules checked:
    1. Base tile requirements: certain tiles need specific base tiles below them
    2. Door adjacency: doors need proper convex corner framing
    3. Convex corner adjacency: convex corners need walkable tiles on appropriate sides

    Args:
        tiles: A 2D numpy array of MetalTile values

    Returns:
        A list of ParseError objects describing any violations found.
    """
    errors: List[ParseError] = []
    height, width = tiles.shape

    # Helper to get tile at position, returns NOTHING if out of bounds
    def get_tile(r: int, c: int) -> MetalTile:
        if 0 <= r < height and 0 <= c < width:
            return MetalTile(tiles[r, c])
        return MetalTile.NOTHING

    # Check base tile requirements
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            if tile in TILES_REQUIRING_BASE:
                required_base = TILES_REQUIRING_BASE[tile]

                # Check if there's a row below
                if row_idx + 1 >= height:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"Tile {tile.name} requires {required_base.name} below, but no row exists",
                        )
                    )
                    continue

                # Check if the tile below is the required base
                tile_below = get_tile(row_idx + 1, col_idx)

                # Allow some flexibility: west/east walls can be below corners
                # (the wall continues down the side)
                if tile in (MetalTile.NW_CORNER, MetalTile.NE_CORNER):
                    # Corners can have west/east walls below them instead of base
                    if tile_below in (MetalTile.WEST_WALL, MetalTile.EAST_WALL):
                        continue

                # CONVEX_SW and CONVEX_SE can have NORTH_WALL_BASE below when
                # they're part of the north wall row (adjacent to north doors)
                if tile in (MetalTile.CONVEX_SW, MetalTile.CONVEX_SE):
                    if tile_below == MetalTile.NORTH_WALL_BASE:
                        continue

                if tile_below != required_base:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"Tile {tile.name} requires {required_base.name} below, "
                            f"but found {tile_below.name}",
                        )
                    )

    # Check door adjacency requirements
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            # West door rules
            if tile == MetalTile.WEST_DOOR_NORTH:
                tile_above = get_tile(row_idx - 1, col_idx)
                if tile_above != MetalTile.CONVEX_SE:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"WEST_DOOR_NORTH requires CONVEX_SE above, but found {tile_above.name}",
                        )
                    )

            if tile == MetalTile.WEST_DOOR_SOUTH:
                tile_below = get_tile(row_idx + 1, col_idx)
                if tile_below != MetalTile.CONVEX_NE:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"WEST_DOOR_SOUTH requires CONVEX_NE below, but found {tile_below.name}",
                        )
                    )

            # East door rules
            if tile == MetalTile.EAST_DOOR_NORTH:
                tile_above = get_tile(row_idx - 1, col_idx)
                if tile_above != MetalTile.CONVEX_SW:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"EAST_DOOR_NORTH requires CONVEX_SW above, but found {tile_above.name}",
                        )
                    )

            if tile == MetalTile.EAST_DOOR_SOUTH:
                tile_below = get_tile(row_idx + 1, col_idx)
                if tile_below != MetalTile.CONVEX_NW:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"EAST_DOOR_SOUTH requires CONVEX_NW below, but found {tile_below.name}",
                        )
                    )

            # North door rules
            if tile == MetalTile.NORTH_DOOR_WEST:
                tile_left = get_tile(row_idx, col_idx - 1)
                if tile_left != MetalTile.CONVEX_NE:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"NORTH_DOOR_WEST requires CONVEX_NE to the left, but found {tile_left.name}",
                        )
                    )

            if tile == MetalTile.NORTH_DOOR_EAST:
                tile_right = get_tile(row_idx, col_idx + 1)
                if tile_right != MetalTile.CONVEX_NW:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"NORTH_DOOR_EAST requires CONVEX_NW to the right, but found {tile_right.name}",
                        )
                    )

            # South door rules
            if tile == MetalTile.SOUTH_DOOR_WEST:
                tile_left = get_tile(row_idx, col_idx - 1)
                if tile_left != MetalTile.CONVEX_SE:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"SOUTH_DOOR_WEST requires CONVEX_SE to the left, but found {tile_left.name}",
                        )
                    )

            if tile == MetalTile.SOUTH_DOOR_EAST:
                tile_right = get_tile(row_idx, col_idx + 1)
                if tile_right != MetalTile.CONVEX_SW:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"SOUTH_DOOR_EAST requires CONVEX_SW to the right, but found {tile_right.name}",
                        )
                    )

    # Check orphaned base tiles (base tiles without their expected tile above)
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            if tile in BASE_TILES_EXPECTED_ABOVE:
                expected_above = BASE_TILES_EXPECTED_ABOVE[tile]

                # Check if there's a row above
                if row_idx - 1 < 0:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"Base tile {tile.name} has no row above",
                        )
                    )
                    continue

                tile_above = get_tile(row_idx - 1, col_idx)

                # Special case: NORTH_WALL_BASE can also be below west/east walls
                # (at NW/NE corners where the wall continues down)
                if tile == MetalTile.NORTH_WALL_BASE:
                    if tile_above in (MetalTile.WEST_WALL, MetalTile.EAST_WALL):
                        continue

                if tile_above not in expected_above:
                    expected_names = ", ".join(t.name for t in expected_above)
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"Base tile {tile.name} requires one of [{expected_names}] above, "
                            f"but found {tile_above.name}",
                        )
                    )

    # Check convex corner adjacency requirements
    # Convex corners need walkable tiles on the sides that "poke" into the room
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            # CONVEX_SW pokes toward SW, so needs walkable to south and west
            if tile == MetalTile.CONVEX_SW:
                tile_south = get_tile(row_idx + 1, col_idx)
                tile_west = get_tile(row_idx, col_idx - 1)
                if tile_south not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_SW requires walkable tile to south, but found {tile_south.name}",
                        )
                    )
                if tile_west not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_SW requires walkable tile to west, but found {tile_west.name}",
                        )
                    )

            # CONVEX_SE pokes toward SE, so needs walkable to south and east
            if tile == MetalTile.CONVEX_SE:
                tile_south = get_tile(row_idx + 1, col_idx)
                tile_east = get_tile(row_idx, col_idx + 1)
                if tile_south not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_SE requires walkable tile to south, but found {tile_south.name}",
                        )
                    )
                if tile_east not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_SE requires walkable tile to east, but found {tile_east.name}",
                        )
                    )

            # CONVEX_NW pokes toward NW, so needs walkable to north and west
            if tile == MetalTile.CONVEX_NW:
                tile_north = get_tile(row_idx - 1, col_idx)
                tile_west = get_tile(row_idx, col_idx - 1)
                if tile_north not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_NW requires walkable tile to north, but found {tile_north.name}",
                        )
                    )
                if tile_west not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_NW requires walkable tile to west, but found {tile_west.name}",
                        )
                    )

            # CONVEX_NE pokes toward NE, so needs walkable to north and east
            if tile == MetalTile.CONVEX_NE:
                tile_north = get_tile(row_idx - 1, col_idx)
                tile_east = get_tile(row_idx, col_idx + 1)
                if tile_north not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_NE requires walkable tile to north, but found {tile_north.name}",
                        )
                    )
                if tile_east not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"CONVEX_NE requires walkable tile to east, but found {tile_east.name}",
                        )
                    )

    # Check wall adjacency requirements
    # Walls need walkable tiles on the interior side (facing into the room)
    # and non-walkable tiles on adjacent sides (forming a continuous wall)
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            # NORTH_WALL: walkable to south (interior), non-walkable to east and west
            if tile == MetalTile.NORTH_WALL:
                tile_south = get_tile(row_idx + 1, col_idx)
                tile_east = get_tile(row_idx, col_idx + 1)
                tile_west = get_tile(row_idx, col_idx - 1)
                if tile_south not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"NORTH_WALL requires walkable tile to south, but found {tile_south.name}",
                        )
                    )
                if tile_east in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"NORTH_WALL requires non-walkable tile to east, but found {tile_east.name}",
                        )
                    )
                if tile_west in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"NORTH_WALL requires non-walkable tile to west, but found {tile_west.name}",
                        )
                    )

            # SOUTH_WALL: walkable to north (interior), non-walkable to east and west
            elif tile == MetalTile.SOUTH_WALL:
                tile_north = get_tile(row_idx - 1, col_idx)
                tile_east = get_tile(row_idx, col_idx + 1)
                tile_west = get_tile(row_idx, col_idx - 1)
                if tile_north not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"SOUTH_WALL requires walkable tile to north, but found {tile_north.name}",
                        )
                    )
                if tile_east in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"SOUTH_WALL requires non-walkable tile to east, but found {tile_east.name}",
                        )
                    )
                if tile_west in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"SOUTH_WALL requires non-walkable tile to west, but found {tile_west.name}",
                        )
                    )

            # EAST_WALL: walkable to west (interior), non-walkable to north and south
            elif tile == MetalTile.EAST_WALL:
                tile_west = get_tile(row_idx, col_idx - 1)
                tile_north = get_tile(row_idx - 1, col_idx)
                tile_south = get_tile(row_idx + 1, col_idx)
                if tile_west not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"EAST_WALL requires walkable tile to west, but found {tile_west.name}",
                        )
                    )
                if tile_north in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"EAST_WALL requires non-walkable tile to north, but found {tile_north.name}",
                        )
                    )
                if tile_south in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"EAST_WALL requires non-walkable tile to south, but found {tile_south.name}",
                        )
                    )

            # WEST_WALL: walkable to east (interior), non-walkable to north and south
            elif tile == MetalTile.WEST_WALL:
                tile_east = get_tile(row_idx, col_idx + 1)
                tile_north = get_tile(row_idx - 1, col_idx)
                tile_south = get_tile(row_idx + 1, col_idx)
                if tile_east not in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"WEST_WALL requires walkable tile to east, but found {tile_east.name}",
                        )
                    )
                if tile_north in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"WEST_WALL requires non-walkable tile to north, but found {tile_north.name}",
                        )
                    )
                if tile_south in WALKABLE_TILES:
                    errors.append(
                        ParseError(
                            row_idx,
                            col_idx,
                            f"WEST_WALL requires non-walkable tile to south, but found {tile_south.name}",
                        )
                    )

    return errors


def fix_tiling_to_valid(tiles: np.ndarray) -> None:
    """
    Transform tiles in-place to satisfy tiling rules.

    This function applies fixes to make the tiling valid:
    1. Adds required base tiles below tiles that need them
    2. Replaces convex corners with straight walls when they don't have
       walkable tiles on the appropriate sides

    Args:
        tiles: A 2D numpy array of MetalTile values (modified in place)
    """
    height, width = tiles.shape

    # Helper to get tile at position, returns NOTHING if out of bounds
    def get_tile(r: int, c: int) -> MetalTile:
        if 0 <= r < height and 0 <= c < width:
            return MetalTile(tiles[r, c])
        return MetalTile.NOTHING

    # Helper to set tile at position (no-op if out of bounds)
    def set_tile(r: int, c: int, tile: MetalTile) -> None:
        if 0 <= r < height and 0 <= c < width:
            tiles[r, c] = tile

    # First pass: fix base tile requirements
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            if tile in TILES_REQUIRING_BASE:
                required_base = TILES_REQUIRING_BASE[tile]

                # Skip if no row below
                if row_idx + 1 >= height:
                    continue

                tile_below = get_tile(row_idx + 1, col_idx)

                # Allow west/east walls below NW/NE corners
                if tile in (MetalTile.NW_CORNER, MetalTile.NE_CORNER):
                    if tile_below in (MetalTile.WEST_WALL, MetalTile.EAST_WALL):
                        continue

                # Allow NORTH_WALL_BASE below CONVEX_SW/CONVEX_SE (north wall row context)
                if tile in (MetalTile.CONVEX_SW, MetalTile.CONVEX_SE):
                    if tile_below == MetalTile.NORTH_WALL_BASE:
                        continue

                # If the tile below is walkable but not the required base, replace it
                if tile_below != required_base and tile_below in WALKABLE_TILES:
                    set_tile(row_idx + 1, col_idx, required_base)

    # Second pass: replace orphaned base tiles with regular floor
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            if tile in BASE_TILES_EXPECTED_ABOVE:
                expected_above = BASE_TILES_EXPECTED_ABOVE[tile]

                # Check if there's a row above
                if row_idx - 1 < 0:
                    # No row above, replace with floor
                    set_tile(row_idx, col_idx, MetalTile.FLOOR)
                    continue

                tile_above = get_tile(row_idx - 1, col_idx)

                # Special case: NORTH_WALL_BASE can also be below west/east walls
                if tile == MetalTile.NORTH_WALL_BASE:
                    if tile_above in (MetalTile.WEST_WALL, MetalTile.EAST_WALL):
                        continue

                # If the tile above is not what we expect, replace with floor
                if tile_above not in expected_above:
                    set_tile(row_idx, col_idx, MetalTile.FLOOR)

    # Helper to determine the best wall replacement based on neighbors
    WALL_TILES = {MetalTile.NORTH_WALL, MetalTile.SOUTH_WALL, MetalTile.WEST_WALL, MetalTile.EAST_WALL}

    def choose_wall_replacement(row_idx: int, col_idx: int, default_wall: MetalTile) -> MetalTile:
        """Choose the best wall type based on neighboring tiles."""
        tile_north = get_tile(row_idx - 1, col_idx)
        tile_south = get_tile(row_idx + 1, col_idx)
        tile_west = get_tile(row_idx, col_idx - 1)
        tile_east = get_tile(row_idx, col_idx + 1)

        # Check horizontal neighbors first (left and right)
        if tile_west in WALL_TILES and tile_east == tile_west:
            return tile_west
        # Check vertical neighbors (above and below)
        if tile_north in WALL_TILES and tile_south == tile_north:
            return tile_north
        # Check if one horizontal neighbor is a wall type
        if tile_west in WALL_TILES and tile_east in WALKABLE_TILES:
            return tile_west
        if tile_east in WALL_TILES and tile_west in WALKABLE_TILES:
            return tile_east
        # Check if one vertical neighbor is a wall type
        if tile_north in WALL_TILES and tile_south in WALKABLE_TILES:
            return tile_north
        if tile_south in WALL_TILES and tile_north in WALKABLE_TILES:
            return tile_south
        # Fall back to default
        return default_wall

    # Third pass: replace invalid convex corners with straight walls
    # We need to iterate until no more changes are made because
    # replacing a convex corner might affect adjacent tiles
    # Limit iterations to prevent infinite loops
    max_iterations = 100
    iteration = 0
    changed = True
    while changed and iteration < max_iterations:
        iteration += 1
        changed = False
        for row_idx in range(height):
            for col_idx in range(width):
                tile = MetalTile(tiles[row_idx, col_idx])

                # CONVEX_SW pokes toward SW, needs walkable to south and west
                if tile == MetalTile.CONVEX_SW:
                    tile_south = get_tile(row_idx + 1, col_idx)
                    tile_west = get_tile(row_idx, col_idx - 1)
                    if tile_south not in WALKABLE_TILES or tile_west not in WALKABLE_TILES:
                        replacement = choose_wall_replacement(row_idx, col_idx, MetalTile.EAST_WALL)
                        set_tile(row_idx, col_idx, replacement)
                        changed = True

                # CONVEX_SE pokes toward SE, needs walkable to south and east
                elif tile == MetalTile.CONVEX_SE:
                    tile_south = get_tile(row_idx + 1, col_idx)
                    tile_east = get_tile(row_idx, col_idx + 1)
                    if tile_south not in WALKABLE_TILES or tile_east not in WALKABLE_TILES:
                        replacement = choose_wall_replacement(row_idx, col_idx, MetalTile.WEST_WALL)
                        set_tile(row_idx, col_idx, replacement)
                        changed = True

                # CONVEX_NW pokes toward NW, needs walkable to north and west
                elif tile == MetalTile.CONVEX_NW:
                    tile_north = get_tile(row_idx - 1, col_idx)
                    tile_west = get_tile(row_idx, col_idx - 1)
                    if tile_north not in WALKABLE_TILES or tile_west not in WALKABLE_TILES:
                        replacement = choose_wall_replacement(row_idx, col_idx, MetalTile.EAST_WALL)
                        set_tile(row_idx, col_idx, replacement)
                        changed = True

                # CONVEX_NE pokes toward NE, needs walkable to north and east
                elif tile == MetalTile.CONVEX_NE:
                    tile_north = get_tile(row_idx - 1, col_idx)
                    tile_east = get_tile(row_idx, col_idx + 1)
                    if tile_north not in WALKABLE_TILES or tile_east not in WALKABLE_TILES:
                        replacement = choose_wall_replacement(row_idx, col_idx, MetalTile.WEST_WALL)
                        set_tile(row_idx, col_idx, replacement)
                        changed = True

    # Fourth pass: replace any newly orphaned base tiles (after convex corner replacement)
    for row_idx in range(height):
        for col_idx in range(width):
            tile = MetalTile(tiles[row_idx, col_idx])

            if tile in BASE_TILES_EXPECTED_ABOVE:
                expected_above = BASE_TILES_EXPECTED_ABOVE[tile]

                # Check if there's a row above
                if row_idx - 1 < 0:
                    set_tile(row_idx, col_idx, MetalTile.FLOOR)
                    continue

                tile_above = get_tile(row_idx - 1, col_idx)

                # Special case: NORTH_WALL_BASE can also be below west/east walls
                if tile == MetalTile.NORTH_WALL_BASE:
                    if tile_above in (MetalTile.WEST_WALL, MetalTile.EAST_WALL):
                        continue

                # If the tile above is not what we expect, replace with floor
                if tile_above not in expected_above:
                    set_tile(row_idx, col_idx, MetalTile.FLOOR)


def parse_metal_ascii_room(ascii_art: List[str]) -> Tuple[List[List[MetalTile]], List[ParseError]]:
    """
    Parse ASCII art into a 2D array of MetalTile values.

    Returns:
        A tuple of (tiles, errors) where tiles is the 2D array and
        errors is a list of validation errors found.
    """
    if not ascii_art:
        return [], [ParseError(0, 0, "Empty ASCII art")]

    width = max(len(line) for line in ascii_art)
    height = len(ascii_art)

    # First pass: convert characters to tiles
    tiles: List[List[MetalTile]] = []
    errors: List[ParseError] = []

    for row_idx, line in enumerate(ascii_art):
        row: List[MetalTile] = []
        for col_idx, char in enumerate(line):
            if char not in METAL_ASCII_TO_TILE:
                errors.append(ParseError(row_idx, col_idx, f"Unknown character: '{char}'"))
                row.append(MetalTile.NOTHING)
            else:
                row.append(METAL_ASCII_TO_TILE[char])

        # Pad row to width if needed
        while len(row) < width:
            row.append(MetalTile.NOTHING)

        tiles.append(row)

    # Convert to numpy array for validation
    tiles_array = np.array([[int(t) for t in row] for row in tiles], dtype=int)

    # Validate using check_valid_tiling
    errors.extend(check_valid_tiling(tiles_array))

    return tiles, errors


def validate_metal_room(ascii_art: List[str]) -> List[ParseError]:
    """
    Validate ASCII art without returning the parsed tiles.

    Convenience function for checking room definitions.
    """
    _, errors = parse_metal_ascii_room(ascii_art)
    return errors


# Mapping from MetalTile values to sprite names for rendering
TILE_MAP: Dict[int, str] = {
    MetalTile.FLOOR: "floor",
    MetalTile.NORTH_WALL_BASE: "north_wall_base",
    MetalTile.PILLAR_BASE: "pillar_base",
    MetalTile.CONVEX_SW_BASE: "convex_sw_base",
    MetalTile.CONVEX_SE_BASE: "convex_se_base",
    MetalTile.NORTH_WALL: "wall_north",
    MetalTile.SOUTH_WALL: "wall_south",
    MetalTile.WEST_WALL: "wall_west",
    MetalTile.EAST_WALL: "wall_east",
    MetalTile.NW_CORNER: "wall_nw_corner",
    MetalTile.NE_CORNER: "wall_ne_corner",
    MetalTile.SW_CORNER: "wall_sw_corner",
    MetalTile.SE_CORNER: "wall_se_corner",
    MetalTile.CONVEX_NW: "convex_nw",
    MetalTile.CONVEX_NE: "convex_ne",
    MetalTile.CONVEX_SW: "convex_sw",
    MetalTile.CONVEX_SE: "convex_se",
    MetalTile.PILLAR: "pillar",
    # Door rendering:
    # - North doors are in the north_wall_base row (below north wall)
    # - South doors render as floor
    # - West/East door north halves render as convex base tiles (they're in shadow row)
    # - West/East door south halves render as floor
    MetalTile.NORTH_DOOR_WEST: "floor",
    MetalTile.NORTH_DOOR_EAST: "floor",
    MetalTile.SOUTH_DOOR_WEST: "floor",
    MetalTile.SOUTH_DOOR_EAST: "floor",
    MetalTile.WEST_DOOR_NORTH: "convex_se_base",  # In shadow row, needs convex_se above
    MetalTile.WEST_DOOR_SOUTH: "floor",
    MetalTile.EAST_DOOR_NORTH: "convex_sw_base",  # In shadow row, needs convex_sw above
    MetalTile.EAST_DOOR_SOUTH: "floor",
    MetalTile.NOTHING: "",  # Empty string means don't render
}

SPRITE_OFFSETS: Dict[str, Sprite] = {
    "wall_nw_corner": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=0, y=0
    ),
    "wall_ne_corner": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=576, y=0
    ),
    "wall_sw_corner": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=0, y=576
    ),
    "wall_se_corner": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=576, y=576
    ),
    "wall_north": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=64, y=0),
    "wall_south": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=64, y=576),
    "wall_west": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=0, y=64),
    "wall_east": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=576, y=64),
    # North walls should always have a walkable north_wall_base
    # tile just to the south of them
    # TODO: write a test to assert this for metal_labyrinth
    # rooms
    "north_wall_base": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=64, y=64
    ),
    "floor": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=64, y=128),
    "pillar": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=128, y=128),
    # pillars should always have a walkable pillar_base just
    # to the south of them.
    # TODO: write a unit test to assert this
    "pillar_base": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=128, y=192
    ),
    # Convex corners are in the same spots as their
    # regular counterparts, so "nw" pokes toward the south east
    "convex_se": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=192, y=640),
    # convex_se should always have a convex_se_base to the south
    "convex_se_base": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=192, y=704
    ),
    "convex_sw": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=384, y=640),
    # convex_sw should always have a walkable convex_sw_base to the south
    "convex_sw_base": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png", x=384, y=704
    ),
    "convex_ne": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=192, y=576),
    "convex_nw": Sprite(file="sprites/metal-labyrinth-paradigm-room.png", x=384, y=576),
    # Hero
    # Hero Walk Cycles (spaceman)
    # South
    "hero_south_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=192, y=0),
    "hero_south_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=256, y=0),
    # North
    "hero_north_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=320, y=0),
    "hero_north_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=384, y=0),
    # West
    "hero_west_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=448, y=0),
    "hero_west_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=512, y=0),
    # East
    "hero_east_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=576, y=0),
    "hero_east_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=640, y=0),
    # NPC sprites and walk cycles
    "npc_default": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=0, y=128
    ),
    # South
    "npc_south_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=192, y=128
    ),
    "npc_south_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=256, y=128
    ),
    # North
    "npc_north_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=320, y=128
    ),
    "npc_north_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=384, y=128
    ),
    # West
    "npc_west_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=448, y=128
    ),
    "npc_west_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=512, y=128
    ),
    # East
    "npc_east_0": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=576, y=128
    ),
    "npc_east_1": Sprite(
        file="sprites/spaceman_overworld_64x64.png", x=640, y=128
    ),
    # Goal
    # TODO: replace this with a television that turns on
    "goal": Sprite(file="sprites/red_heart.png", x=0, y=0),
    "robot_priest": Sprite(
        file="sprites/metal-labyrinth-paradigm-room.png",
        x=640,
        y=448,
        width=128,
        height=192,
        base_width=128,
        offset_y=-32,
        # TODO: We'd like to add a base_offset_y here
        # as well. It would be nice for the hero
        # to be able to walk on top of the
        # bottom 32 pixels of this sprite but
        # treat the next 64x128 pixels as the location
        # of the NPC
    ),
    # TODO: redo this portrait art
    "robot_priest_portrait": Sprite(
        file="portraits/npc_portraits_01.png",
        x=0,
        y=0,
        width=256,
        height=256,
    ),
}

# Static lookup for hero sprites: [direction][frame]
# Directions: 0=East, 1=South, 2=West, 3=North
# TODO: prefer a direction enumeration to these numbers
HERO_WALK_CYCLES: Tuple[Tuple[str, str], ...] = (
    ("hero_east_0", "hero_east_1"),  # 0: East
    ("hero_south_0", "hero_south_1"),  # 1: South
    ("hero_west_0", "hero_west_1"),  # 2: West
    ("hero_north_0", "hero_north_1"),  # 3: North
)

@dataclass
class MetalRoomTemplate:
    """
    Room template for metal labyrinth using the MetalTile system.

    Similar to RoomTemplate but uses the metal labyrinth ASCII dialect
    and validates base tile requirements.
    """

    name: str
    ascii_art: List[str]

    @property
    def width(self) -> int:
        return max(len(line) for line in self.ascii_art) if self.ascii_art else 0

    @property
    def height(self) -> int:
        return len(self.ascii_art)

    @property
    def has_north_door(self) -> bool:
        return any("n" in line or "N" in line for line in self.ascii_art)

    @property
    def has_south_door(self) -> bool:
        return any("s" in line or "S" in line for line in self.ascii_art)

    @property
    def has_east_door(self) -> bool:
        return any("e" in line or "E" in line for line in self.ascii_art)

    @property
    def has_west_door(self) -> bool:
        return any("w" in line or "W" in line for line in self.ascii_art)

    def parse(self) -> Tuple[List[List[MetalTile]], List[ParseError]]:
        """Parse this template's ASCII art into tiles."""
        return parse_metal_ascii_room(self.ascii_art)

    def validate(self) -> List[ParseError]:
        """Validate this template's ASCII art."""
        return validate_metal_room(self.ascii_art)


# TODO: Door replacement code needs to manage
# corners around doors! Right now it'll look pretty weird.

# The metal_labyrinth rooms use a different
# tile set than the death_mountain rooms,
# and need their own ascii art decoding.
#
# Example room (12x10, large):
#
#   Row 0: 1----nN----2   <- corners and north wall with door
#   Row 1: [,,,,,,,,,,]   <- west wall, north wall bases, east wall
#   Row 2: [..........]   <- west wall, floor, east wall
#   ...
#   Row 9: 3____sS____4   <- corners and south wall with door
#
METAL_ROOM_TEMPLATES: List[MetalRoomTemplate] = [
    MetalRoomTemplate(
        name="large",
        ascii_art=[
            "1---`nN~---2",
            "[,,,,..,,,,]",
            "[..........]",
            "`..........~",
            "w..........e",
            "W..........E",
            "!..........^",
            "[..........]",
            "[..........]",
            "3___!sS^___4",
        ],
    ),
    MetalRoomTemplate(
        name="pillars",
        ascii_art=[
            "1-`nN~-2",
            "[,,..,,]",
            "[......]",
            "`..P...~",
            "w..;...e",
            "W...P..E",
            "!...;..^",
            "[......]",
            "[......]",
            "3_!sS^_4",
        ],
    ),
    MetalRoomTemplate(
        name="donut",
        ascii_art=[
            "1----`nN~----2",
            "[,,,,,..,,,,,]",
            "[............]",
            "`....^__!....~",
            "w....]  [....e",
            "W....]  [....E",
            "!....~--`....^",
            "[....<,,>....]",
            "[............]",
            "3____!sS^____4",
        ],
    ),
    # TODO: This room isn't valid because there
    # aren't corners around the doors, but I
    # think it'll look just fine.
    # We need to reconsider what door sides must look like.
    MetalRoomTemplate(
        name="east-west",
        ascii_art=[
            "1-------2",
            "w,,,,,,,e",
            "W.......E",
            "3_______4",
        ],
    ),
    MetalRoomTemplate(
        name="long-east-west",
        ascii_art=[
            "1--------------------2",
            "w,,,,,,,,,,,,,,,,,,,,e",
            "W....................E",
            "3____________________4",
        ],
    ),
    MetalRoomTemplate(
        name="north-south",
        ascii_art=[
            "1nN2",
            "[..]",
            "[..]",
            "[..]",
            "[..]",
            "[..]",
            "[..]",
            "3sS4",
        ],
    ),
    # TODO: add a diamond room
    # and some more interesting rooms here please
]