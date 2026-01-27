from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional, Tuple, Protocol

from .sprite import Sprite


# TODO: Dungeon generation is now much too slow, it causes the
# stream to lag. We need to make sure it is a lot faster.


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
    # Walls are named for the side of the room they are on,
    # so a WEST_WALL is on the west side of a room, facing east.
    NORTH_WALL = 10  # wall along the top of a room
    SOUTH_WALL = 11  # wall along the bottom of a room
    WEST_WALL = 12  # the left-most wall of a room
    EAST_WALL = 13  # the right-most wall of a room

    # Corners (non-walkable)
    NW_CORNER = 20  # the joint between a west wall and a north wall
    NE_CORNER = 21  # the joint between a north wall and an east wall
    SW_CORNER = 22  # the joint between a west wall and a south wall
    SE_CORNER = 23  # the joint between a south wall and an east wall

    # Convex corners for interior cutouts (non-walkable)
    # Convex corners are named for the direction they point,
    # so CONVEX_NW points towards the northwest corner of the
    # dungeon.
    CONVEX_NW = 30  # Where a SOUTH_WALL meets an EAST_WALL
    CONVEX_NE = 31  # Where a SOUTH_WALL meets a WEST_WALL
    CONVEX_SW = 32  # Where a NORTH_WALL meets an EAST_WALL
    CONVEX_SE = 33  # Where a NORTH_WALL meets a WEST_WALL

    # Pillar (non-walkable)
    PILLAR = 40

    # Doors (walkable, used for room navigation)
    # These render as floor but are tracked for pathfinding
    # NORTH_DOORs are on the north (topmost) wall
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

# Reverse mapping from MetalTile IDs to ASCII characters
# Kept in sync with METAL_ASCII_TO_TILE for ASCII rendering
TILE_TO_ASCII: Dict[MetalTile, str] = {
    MetalTile.NOTHING: " ",
    # Corners
    MetalTile.NW_CORNER: "1",
    MetalTile.NE_CORNER: "2",
    MetalTile.SW_CORNER: "3",
    MetalTile.SE_CORNER: "4",
    # Walls
    MetalTile.NORTH_WALL: "-",
    MetalTile.SOUTH_WALL: "_",
    MetalTile.WEST_WALL: "[",
    MetalTile.EAST_WALL: "]",
    # Floor tiles
    MetalTile.FLOOR: ".",
    MetalTile.NORTH_WALL_BASE: ",",
    MetalTile.PILLAR_BASE: ";",
    MetalTile.CONVEX_SW_BASE: "<",
    MetalTile.CONVEX_SE_BASE: ">",
    # Convex corners
    MetalTile.CONVEX_NW: "^",
    MetalTile.CONVEX_NE: "!",
    MetalTile.CONVEX_SW: "~",
    MetalTile.CONVEX_SE: "`",
    # Pillar
    MetalTile.PILLAR: "P",
    # Doors
    MetalTile.NORTH_DOOR_WEST: "n",
    MetalTile.NORTH_DOOR_EAST: "N",
    MetalTile.SOUTH_DOOR_WEST: "s",
    MetalTile.SOUTH_DOOR_EAST: "S",
    MetalTile.WEST_DOOR_NORTH: "w",
    MetalTile.WEST_DOOR_SOUTH: "W",
    MetalTile.EAST_DOOR_NORTH: "e",
    MetalTile.EAST_DOOR_SOUTH: "E",
}


def render_dungeon_ascii(dungeon_map) -> str:
    """
    Convert a dungeon map (numpy array of MetalTile values) to ASCII string.

    Args:
        dungeon_map: 2D numpy array of MetalTile values

    Returns:
        ASCII art representation of the dungeon
    """
    lines = []
    rows, cols = dungeon_map.shape
    for row in range(rows):
        line = ""
        for col in range(cols):
            tile = dungeon_map[row, col]
            char = TILE_TO_ASCII.get(tile, "?")
            line += char
        lines.append(line)
    return "\n".join(lines)


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

@dataclass
class ParseError:
    """Error found during ASCII art parsing."""

    row: int
    column: int
    message: str


def parse_metal_ascii_room(
    ascii_art: List[str],
) -> Tuple[List[List[MetalTile]], List[ParseError]]:
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
                errors.append(
                    ParseError(row_idx, col_idx, f"Unknown character: '{char}'")
                )
                row.append(MetalTile.NOTHING)
            else:
                row.append(METAL_ASCII_TO_TILE[char])

        # Pad row to width if needed
        while len(row) < width:
            row.append(MetalTile.NOTHING)

        tiles.append(row)

    return tiles, errors


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
    "npc_default": Sprite(file="sprites/spaceman_overworld_64x64.png", x=0, y=128),
    # South
    "npc_south_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=192, y=128),
    "npc_south_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=256, y=128),
    # North
    "npc_north_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=320, y=128),
    "npc_north_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=384, y=128),
    # West
    "npc_west_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=448, y=128),
    "npc_west_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=512, y=128),
    # East
    "npc_east_0": Sprite(file="sprites/spaceman_overworld_64x64.png", x=576, y=128),
    "npc_east_1": Sprite(file="sprites/spaceman_overworld_64x64.png", x=640, y=128),
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
            "[,,,>..<,,,]",
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
            "[,>..<,]",
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
            "[,,,,>..<,,,,]",
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
    MetalRoomTemplate(
        name="dog-bone",
        ascii_art=[
            "1--2              1--2",
            "`,,~--------------`,,~",
            "w..<,,,,,,,,,,,,,,>..e",
            "W....................E",
            "!..^______________!..^",
            "3__4              3__4",
        ],
    ),
    MetalRoomTemplate(
        name="north-south",
        ascii_art=[
            "[nN]",
            "[..]",
            "[..]",
            "[..]",
            "[..]",
            "[..]",
            "[..]",
            "[sS]",
        ],
    ),
]


"""
    These rooms violate some of our assumptions
    about valid rooms.

    MetalRoomTemplate(
        name="cross",
        ascii_art=[
            "    1-`nN~-2    ",
            "    [,,..,,]    ",
            "    [......]    ",
            "1---!......^---2",
            "w,,,,......,,,,e",
            "W..............E",
            "3---^......!---4",
            "    [......]    ",
            "    [......]    ",
            "    3_!sS^_4    ",
        ],
    ),
    MetalRoomTemplate(
        name="zigzag",
        ascii_art=[
            "1------`nN~-2",
            "[,,,,,,,...,]",
            "[..........]",
            "[..........]",
            "[......^---4",
            "[w....._____",
            "[W..........e",
            "[!..........E",
            "1-~.........^",
            "--,........._",
            "[,,.........]",
            "[...........]",
            "[...........]",
            "3_____!sS^__4",
        ],
    ),
    MetalRoomTemplate(
        name="cathedral",
        ascii_art=[
            "1----`nN~----2",
            "[,,,,,..,,,,,]",
            "[.P.........P]",
            "[.;.........;]",
            "`..P.......P.~",
            "w..;.......;.e",
            "W...P.....P..E",
            "!...;.....;..^",
            "[............]",
            "[............]",
            "3____!sS^____4",
        ],
    ),
    MetalRoomTemplate(
        name="alcoves",
        ascii_art=[
            "1-----`nN~-----2",
            "[,,,,,,..,,,,,]",
            "[P............P]",
            "[;............;]",
            "`..^--------!..~",
            "w..~........`..e",
            "W..!........^..E",
            "!..`--------~..^",
            "[..............]",
            "[..............]",
            "3_____!sS^_____4",
        ],
    ),
    """
