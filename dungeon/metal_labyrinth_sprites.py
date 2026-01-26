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
    MetalTile.GOAL,
}

# Door slot characters (for detecting doors in templates)
METAL_DOOR_CHARS = {"n", "N", "s", "S", "w", "W", "e", "E"}


@dataclass
class ParseError:
    """Error found during ASCII art parsing."""

    row: int
    column: int
    message: str


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

    # Second pass: validate base tile requirements
    for row_idx in range(height):
        for col_idx in range(width):
            tile = tiles[row_idx][col_idx]

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
                tile_below = tiles[row_idx + 1][col_idx]

                # Allow some flexibility: west/east walls can be below corners
                # (the wall continues down the side)
                if tile in (MetalTile.NW_CORNER, MetalTile.NE_CORNER):
                    # Corners can have west/east walls below them instead of base
                    if tile_below in (MetalTile.WEST_WALL, MetalTile.EAST_WALL):
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

    return tiles, errors


def validate_metal_room(ascii_art: List[str]) -> List[ParseError]:
    """
    Validate ASCII art without returning the parsed tiles.

    Convenience function for checking room definitions.
    """
    _, errors = parse_metal_ascii_room(ascii_art)
    return errors


# TODO: you need custom metal labyrinth tiling as well,
# so you can tile walkables like pillar base, north edge floor, etc

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
        offset_y=32,
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
            "1----nN----2",
            "[,,,,,,,,,,]",
            "[..........]",
            "[..........]",
            "w..........e",
            "W..........E",
            "[..........]",
            "[..........]",
            "[..........]",
            "3____sS____4",
        ],
    ),
    MetalRoomTemplate(
        name="pillars",
        ascii_art=[
            "1--nN--2",
            "[,,,,,,]",
            "[......]",
            "[..P...]",
            "w..;...e",
            "W...P..E",
            "[...;..]",
            "[......]",
            "[......]",
            "3__sS__4",
        ],
    ),
    MetalRoomTemplate(
        name="donut",
        ascii_art=[
            "1-----nN-----2",
            "[,,,,,,,,,,,,]",
            "[............]",
            "[....^__!....]",
            "w....]  [....e",
            "W....]  [....E",
            "[....~--`....]",
            "[....<,,>....]",
            "[............]",
            "3_____sS_____4",
        ],
    ),
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