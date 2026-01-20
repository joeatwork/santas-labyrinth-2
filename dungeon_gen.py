"""
Dungeon Generation Algorithm
============================

We grow the dungeon organically by connecting rooms through their doors.

1. Start with a single room at position (0, 0) - the start room
   - Place it with all possible doors enabled
2. Keep a queue of "open doors" (doors that don't have corridors/rooms attached yet)
3. While we haven't reached our target number of rooms:
   a. Pick an open door from the queue
   b. Pick a random room template that has a corresponding door (north to south, east to west)
   c. Try to place the random room so that the doors line up
   d. If it would overlap, mark this door as "blocked" and try another open door
4. Place the goal in the last room added
5. Replace all unconnected doors with walls (no "blind doors" that lead nowhere)
"""

import random
import numpy as np
from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple, List, Dict, Set, Optional


# Tile Constants (Matching animation.py expectations or defining new ones)
# TODO: Tile mixes logical, map tiles (like NORTH_DOOR_WEST) with rendeing
# implementation details like NORTH_DOORFRAME_WEST. These should be distinct
# types (and dungeon generation shouldn't know that foregrounds and backgrounds exist.)
class Tile:
    NOTHING: int = 0
    FLOOR: int = 1
    NORTH_WALL: int = 10
    SOUTH_WALL: int = 11
    WEST_WALL: int = 12
    EAST_WALL: int = 13
    NW_CORNER: int = 14
    NE_CORNER: int = 15
    SW_CORNER: int = 16
    SE_CORNER: int = 17

    PILLAR: int = 50
    NW_CONVEX_CORNER: int = 51
    NE_CONVEX_CORNER: int = 52
    SW_CONVEX_CORNER: int = 53
    SE_CONVEX_CORNER: int = 54

    DECORATIVE_NORTH_WALL_0: int = 60
    DECORATIVE_NORTH_WALL_1: int = 61
    DECORATIVE_NORTH_WALL_2: int = 62
    DECORATIVE_NORTH_WALL_3: int = 63

    # Doors (each direction has two tiles - west/east or north/south halves)
    NORTH_DOOR_WEST: int = 20
    NORTH_DOOR_EAST: int = 21
    SOUTH_DOOR_WEST: int = 22
    SOUTH_DOOR_EAST: int = 23
    WEST_DOOR_NORTH: int = 24
    WEST_DOOR_SOUTH: int = 25
    EAST_DOOR_NORTH: int = 26
    EAST_DOOR_SOUTH: int = 27

    # Goal
    GOAL: int = 30

    # Doorframes (foreground tiles)
    NORTH_DOORFRAME_WEST: int = 40
    NORTH_DOORFRAME_EAST: int = 41
    SOUTH_DOORFRAME_WEST: int = 42
    SOUTH_DOORFRAME_EAST: int = 43
    WEST_DOORFRAME_NORTH: int = 44
    WEST_DOORFRAME_SOUTH: int = 45
    EAST_DOORFRAME_NORTH: int = 46
    EAST_DOORFRAME_SOUTH: int = 47


# Room size in tiles (from references)
ROOM_WIDTH: int = 12
ROOM_HEIGHT: int = 10

# ASCII character to tile mapping
ASCII_TO_TILE: Dict[str, int] = {
    " ": Tile.NOTHING,
    ".": Tile.FLOOR,
    "-": Tile.NORTH_WALL,
    "_": Tile.SOUTH_WALL,
    "[": Tile.WEST_WALL,
    "]": Tile.EAST_WALL,
    "=": Tile.DECORATIVE_NORTH_WALL_0,
    "#": Tile.DECORATIVE_NORTH_WALL_1,
    "+": Tile.DECORATIVE_NORTH_WALL_2,
    "*": Tile.DECORATIVE_NORTH_WALL_3,
    "1": Tile.NW_CORNER,
    "2": Tile.NE_CORNER,
    "3": Tile.SW_CORNER,
    "4": Tile.SE_CORNER,
    "P": Tile.PILLAR,
    "^": Tile.NW_CONVEX_CORNER,
    "!": Tile.NE_CONVEX_CORNER,
    "~": Tile.SW_CONVEX_CORNER,
    ",": Tile.SE_CONVEX_CORNER,
    "n": Tile.NORTH_DOOR_WEST,
    "N": Tile.NORTH_DOOR_EAST,
    "s": Tile.SOUTH_DOOR_WEST,
    "S": Tile.SOUTH_DOOR_EAST,
    "w": Tile.WEST_DOOR_NORTH,
    "W": Tile.WEST_DOOR_SOUTH,
    "e": Tile.EAST_DOOR_NORTH,
    "E": Tile.EAST_DOOR_SOUTH,
}

# Door slot characters (converted to door tiles or walls based on required connections)
DOOR_SLOT_CHARS = {"n", "N", "s", "S", "w", "W", "e", "E"}


@dataclass(frozen=True)
class Position:
    """A position in the dungeon grid, measured in tiles."""

    row: int
    column: int


class Direction(Enum):
    """Cardinal directions for door placement and room connections."""

    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()

    def opposite(self) -> "Direction":
        """Returns the opposite direction."""
        opposites = {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }
        return opposites[self]

    def step(self) -> Position:
        """Returns the Position offset for moving one step in this direction."""
        steps = {
            Direction.NORTH: Position(row=-1, column=0),
            Direction.SOUTH: Position(row=1, column=0),
            Direction.EAST: Position(row=0, column=1),
            Direction.WEST: Position(row=0, column=-1),
        }
        return steps[self]


@dataclass
class RoomTemplate:
    """Defines a room shape using ASCII art."""

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

    def has_door(self, direction: Direction) -> bool:
        """Check if this template has a door in the given direction."""
        door_checks = {
            Direction.NORTH: self.has_north_door,
            Direction.SOUTH: self.has_south_door,
            Direction.EAST: self.has_east_door,
            Direction.WEST: self.has_west_door,
        }
        return door_checks[direction]

    def has_matching_door(self, direction: Direction) -> bool:
        """Check if this template has a door that can connect to the given direction.

        For example, if direction is NORTH (an existing room's north door),
        this returns True if this template has a SOUTH door to connect to it.
        """
        return self.has_door(direction.opposite())


# Pre-defined room templates
ROOM_TEMPLATES: List[RoomTemplate] = [
    RoomTemplate(
        name="large",
        ascii_art=[
            "1----nN----2",
            "[..........]",
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
    RoomTemplate(
        name="medium",
        ascii_art=[
            "1--nN--2",
            "[......]",
            "[.P....]",
            "w......e",
            "W......E",
            "[......]",
            "[....P.]",
            "3__sS__4",
        ],
    ),
    RoomTemplate(
        name="wide",
        ascii_art=[
            "1-----nN-----2",
            "[............]",
            "w............e",
            "W............E",
            "[............]",
            "3_____sS_____4",
        ],
    ),
    RoomTemplate(
        name="big-pillar",
        ascii_art=[
            "1-----nN-----2",
            "[............]",
            "w.....^!.....e",
            "W.....~,.....E",
            "[............]",
            "3_____sS_____4",
        ],
    ),
    RoomTemplate(
        name="small-pillars",
        ascii_art=[
            "1----nN----2",
            "[..........]",
            "[...P..P...]",
            "[..........]",
            "w..........e",
            "W..........E",
            "[..........]",
            "[...P..P...]",
            "[..........]",
            "3____sS____4",
        ],
    ),
    RoomTemplate(
        name="east-west",
        ascii_art=[
            "1---*---2",
            "w.......e",
            "W.......E",
            "3_______4",
        ],
    ),
    RoomTemplate(
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
    RoomTemplate(
        name="diamond",
        ascii_art=[
            "  1-nN-2  ",
            " 1,....~2 ",
            "1,......~2",
            "w........e",
            "W........E",
            "3!......^4",
            " 3!....^4 ",
            "  3_sS_4  ",
        ]
    ),
    RoomTemplate(
        name="big-el",
        ascii_art=[
            "1-nN-2",
            "[....]",
            "[....]",
            "[....]",
            "[....~------2",
            "[...........e",
            "[...........E",
            "3___________4",
        ],
    ),
    RoomTemplate(
        name="big-jay",
        ascii_art=[
            "       1-nN-2",
            "       [....]",
            "       [....]",
            "       [....]",
            "1------,....]",
            "w...........]",
            "W...........]",
            "3___________4",
        ],
    ) 
]


def _parse_ascii_room(
    template: RoomTemplate,
) -> List[List[int]]:
    """
    Parse an ASCII room template into a 2D tile array.

    Door slot characters are converted to door tiles if the corresponding
    door is needed, otherwise to wall tiles.
    """
    tiles: List[List[int]] = []

    for row_idx, line in enumerate(template.ascii_art):
        row = [ASCII_TO_TILE[chr] for chr in line]

        # Pad row to template width if needed
        while len(row) < template.width:
            row.append(Tile.NOTHING)

        tiles.append(row)

    return tiles


def _get_door_position(
    template: RoomTemplate, direction: Direction
) -> Optional[Position]:
    """
    Get the tile position of a door slot in the template.

    Returns Position of the first door tile, or None if no door slot exists.
    """
    # Each direction has two door characters (e.g., 'n' and 'N' for north)
    door_chars = {
        Direction.NORTH: ("n", "N"),
        Direction.SOUTH: ("s", "S"),
        Direction.EAST: ("e", "E"),
        Direction.WEST: ("w", "W"),
    }
    target_chars = door_chars[direction]

    for row_idx, line in enumerate(template.ascii_art):
        for col_idx, char in enumerate(line):
            if char in target_chars:
                return Position(row=row_idx, column=col_idx)

    return None


# Type Definition
DungeonMap = np.ndarray


# TODO: this shouldn't be in this file, foregrounds should
# be calculated by the renderer.
def generate_foreground_from_dungeon(dungeon_map: DungeonMap) -> DungeonMap:
    """
    Generates a foreground map from an existing dungeon map by detecting door tiles
    and placing corresponding doorframe arch tiles above them.
    """
    rows, cols = dungeon_map.shape
    foreground: DungeonMap = np.zeros((rows, cols), dtype=int)

    # Direct mapping from door tile to doorframe tile
    door_to_doorframe = {
        Tile.NORTH_DOOR_WEST: Tile.NORTH_DOORFRAME_WEST,
        Tile.NORTH_DOOR_EAST: Tile.NORTH_DOORFRAME_EAST,
        Tile.SOUTH_DOOR_WEST: Tile.SOUTH_DOORFRAME_WEST,
        Tile.SOUTH_DOOR_EAST: Tile.SOUTH_DOORFRAME_EAST,
        Tile.WEST_DOOR_NORTH: Tile.WEST_DOORFRAME_NORTH,
        Tile.WEST_DOOR_SOUTH: Tile.WEST_DOORFRAME_SOUTH,
        Tile.EAST_DOOR_NORTH: Tile.EAST_DOORFRAME_NORTH,
        Tile.EAST_DOOR_SOUTH: Tile.EAST_DOORFRAME_SOUTH,
    }

    for r in range(rows):
        for c in range(cols):
            tile = dungeon_map[r, c]
            if tile in door_to_doorframe:
                foreground[r, c] = door_to_doorframe[tile]

    return foreground


def _place_room_on_canvas(
    canvas: np.ndarray,
    template: RoomTemplate,
    position: Position,
) -> None:
    """Place a room on the canvas at the given position."""
    room_tiles = _parse_ascii_room(template)
    for local_row, row in enumerate(room_tiles):
        for local_column, tile in enumerate(row):
            canvas[position.row + local_row, position.column + local_column] = tile


def _calculate_room_placement(
    direction: Direction, door_position: Position, new_template: RoomTemplate
) -> Position:
    """
    Calculate where a new room should be placed to connect to an existing door.

    Args:
        direction: The direction the existing door faces ('north', 'south', 'east', 'west')
        door_position: Position of the existing door
        new_template: The template for the new room to place

    Returns: Position where the new room's top-left corner should be placed
    """

    target_step = direction.step()
    target_door_offset = Position(
        row=door_position.row + target_step.row,
        column=door_position.column + target_step.column,
    )

    complimentary_direction = direction.opposite()
    complimentary_door = _get_door_position(new_template, complimentary_direction)
    if not complimentary_door:
        raise RuntimeError("cannot place room")

    return Position(
        row=target_door_offset.row - complimentary_door.row,
        column=target_door_offset.column - complimentary_door.column,
    )


def _would_overlap(
    canvas: np.ndarray, template: RoomTemplate, position: Position
) -> bool:
    """Check if placing a room at the given position would overlap existing tiles."""
    for local_row in range(template.height):
        for local_column in range(template.width):
            if (
                canvas[position.row + local_row, position.column + local_column]
                != Tile.NOTHING
            ):
                return True
    return False


def _replace_blind_doors_with_walls(
    dungeon_map: np.ndarray,
    room_positions: Dict[int, Position],
    room_assignments: Dict[int, RoomTemplate],
    connected_doors: Set[Tuple[int, Direction]],
) -> None:
    """
    Replace all unconnected door tiles with appropriate wall tiles.

    Uses the connected_doors set to determine which doors were actually connected,
    rather than making assumptions based on adjacent tiles.
    """
    # Mapping from door tiles to their corresponding wall tiles
    door_to_wall = {
        Tile.NORTH_DOOR_WEST: Tile.NORTH_WALL,
        Tile.NORTH_DOOR_EAST: Tile.NORTH_WALL,
        Tile.SOUTH_DOOR_WEST: Tile.SOUTH_WALL,
        Tile.SOUTH_DOOR_EAST: Tile.SOUTH_WALL,
        Tile.WEST_DOOR_NORTH: Tile.WEST_WALL,
        Tile.WEST_DOOR_SOUTH: Tile.WEST_WALL,
        Tile.EAST_DOOR_NORTH: Tile.EAST_WALL,
        Tile.EAST_DOOR_SOUTH: Tile.EAST_WALL,
    }

    # For each room, check its doors
    for room_id, room_position in room_positions.items():
        template = room_assignments[room_id]

        # Check each direction
        for direction in [
            Direction.NORTH,
            Direction.SOUTH,
            Direction.EAST,
            Direction.WEST,
        ]:
            # Skip if this door was connected
            if (room_id, direction) in connected_doors:
                continue

            # Skip if template doesn't have this door
            if not template.has_door(direction):
                continue

            # Get door position in template
            door_pos = _get_door_position(template, direction)
            if not door_pos:
                continue

            # Calculate absolute position of door tiles
            door_row = room_position.row + door_pos.row
            door_col = room_position.column + door_pos.column

            # Replace door tiles with walls
            # Each door has two tiles (e.g., NORTH_DOOR_WEST and NORTH_DOOR_EAST)
            if direction in [Direction.NORTH, Direction.SOUTH]:
                # North/South doors are two tiles wide
                for col_offset in range(2):
                    tile = dungeon_map[door_row, door_col + col_offset]
                    if tile in door_to_wall:
                        dungeon_map[door_row, door_col + col_offset] = door_to_wall[
                            tile
                        ]

                    # A little extra potential spice if it's a north wall
                    if tile == Tile.NORTH_DOOR_WEST:
                        dungeon_map[door_row, door_col + col_offset] = random.choice([
                            Tile.DECORATIVE_NORTH_WALL_0,
                            Tile.DECORATIVE_NORTH_WALL_1,
                            Tile.DECORATIVE_NORTH_WALL_2,
                        ])
            else:
                # East/West doors are two tiles tall
                for row_offset in range(2):
                    tile = dungeon_map[door_row + row_offset, door_col]
                    if tile in door_to_wall:
                        dungeon_map[door_row + row_offset, door_col] = door_to_wall[
                            tile
                        ]


def find_floor_tile_in_room(
    dungeon_map: np.ndarray,
    room_pos: Position,
    template: RoomTemplate,
) -> Position:
    """
    Find a FLOOR tile within a room, preferring tiles near the center.

    Searches in a spiral pattern starting from the room's center.

    Args:
        dungeon_map: The dungeon tile array
        room_pos: Position of the room's top-left corner
        template: The room's template (for dimensions)

    Returns:
        Position of a FLOOR tile within the room

    Raises:
        RuntimeError: If no FLOOR tile is found in the room
    """
    center_row = room_pos.row + template.height // 2
    center_col = room_pos.column + template.width // 2

    # Check center first
    if dungeon_map[center_row, center_col] == Tile.FLOOR:
        return Position(row=center_row, column=center_col)

    # Spiral outward from center
    for offset in range(1, max(template.height, template.width)):
        for dr in range(-offset, offset + 1):
            for dc in range(-offset, offset + 1):
                if abs(dr) != offset and abs(dc) != offset:
                    continue  # Only check the perimeter of current offset
                row = center_row + dr
                col = center_col + dc
                # Ensure we're within the room bounds
                if (room_pos.row <= row < room_pos.row + template.height and
                    room_pos.column <= col < room_pos.column + template.width):
                    if dungeon_map[row, col] == Tile.FLOOR:
                        return Position(row=row, column=col)

    raise RuntimeError("Failed to find a FLOOR tile in room")


def _crop_dungeon_map(dungeon_map: np.ndarray) -> Tuple[np.ndarray, Position]:
    """
    Crop the dungeon map to the minimum bounding box containing all non-zero tiles.

    Returns: (cropped_map, offset) where offset is the Position of the crop origin
    """
    # Find bounding box
    rows, cols = np.where(dungeon_map != Tile.NOTHING)
    if len(rows) == 0:
        # Empty map
        return dungeon_map[:10, :10], Position(row=0, column=0)

    min_row, max_row = rows.min(), rows.max()
    min_col, max_col = cols.min(), cols.max()

    # Add some padding
    padding = 5
    min_row = max(0, min_row - padding)
    min_col = max(0, min_col - padding)
    max_row = min(dungeon_map.shape[0] - 1, max_row + padding)
    max_col = min(dungeon_map.shape[1] - 1, max_col + padding)

    cropped = dungeon_map[min_row : max_row + 1, min_col : max_col + 1]
    return cropped, Position(row=min_row, column=min_col)


def generate_dungeon(num_rooms: int) -> Tuple[
    DungeonMap,
    Tuple[int, int],
    Dict[int, Tuple[int, int]],
    Dict[int, RoomTemplate],
]:
    """
    Generates a dungeon by organically growing rooms from open doors.

    Uses the ultra-simple algorithm documented at the top of this file.

    Parameters:
        num_rooms: Target number of rooms to generate

    Returns:
        dungeon_map: The tile map
        start_pos_pixel: Starting position in pixels
        room_positions: Dict mapping room_id to (tile_x, tile_y) position
        room_assignments: Dict mapping room_id to RoomTemplate used
    """
    # TODO: ensure that the start position returned from this function is always
    # a walkable tile.

    target_num_rooms = num_rooms

    # We'll use a much larger canvas to avoid worrying about bounds initially
    # Estimate: each room ~12x10, each corridor ~8, max branches ~4 per room
    # Rough estimate: 30 rooms * (12 + 8) * 4 directions = ~2400 tiles per dimension
    canvas_size = max(2000, target_num_rooms * 100)

    # Create empty canvas (we'll crop it later)
    dungeon_map: DungeonMap = np.zeros((canvas_size, canvas_size), dtype=int)

    # Track room information
    room_positions: Dict[int, Position] = {}  # room_id -> Position
    room_assignments: Dict[int, RoomTemplate] = {}  # room_id -> RoomTemplate

    # Track open doors: list of (room_id, direction, door_position)
    open_doors: List[Tuple[int, Direction, Position]] = []

    # Track connected doors: set of (room_id, direction) that were successfully connected
    connected_doors: Set[Tuple[int, Direction]] = set()

    # Start with first room at center of canvas
    start_room_id = 0
    start_position = Position(row=canvas_size // 2, column=canvas_size // 2)
    start_template = random.choice(ROOM_TEMPLATES)

    room_positions[start_room_id] = start_position
    room_assignments[start_room_id] = start_template

    # Place start room on canvas
    _place_room_on_canvas(
        dungeon_map,
        start_template,
        start_position,
    )

    # Add all doors from the start room to the open doors queue
    for direction in [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]:
        door_pos = _get_door_position(start_template, direction)
        if door_pos:
            open_doors.append(
                (
                    start_room_id,
                    direction,
                    Position(
                        row=start_position.row + door_pos.row,
                        column=start_position.column + door_pos.column,
                    ),
                )
            )

    # Keep adding rooms until we reach target
    next_room_id = 1
    last_room_id = start_room_id

    while len(room_assignments) < target_num_rooms and open_doors:
        # Pick a random open door
        if not open_doors:
            break

        # direction: here is "north" for a NORTH_* door,
        # which is on the north edge of the room.
        random.shuffle(open_doors)
        source_room_id, direction, door_position = open_doors.pop()

        # Pick a random room template that has the corresponding door
        matching_templates = [
            room for room in ROOM_TEMPLATES if room.has_matching_door(direction)
        ]
        if not matching_templates:
            break

        random.shuffle(matching_templates)

        new_template = None
        for possible_template in matching_templates:
            possible_room_position = _calculate_room_placement(
                direction, door_position, possible_template
            )

            if not _would_overlap(
                dungeon_map, possible_template, possible_room_position
            ):
                new_room_position = possible_room_position
                new_template = possible_template
                # This placement will work!
                break

        if not new_template:
            # We can't find a template that'll work for this door.
            # give up.
            continue

        # Mark the source door as connected
        connected_doors.add((source_room_id, direction))

        _place_room_on_canvas(
            dungeon_map,
            new_template,
            new_room_position,
        )
        room_positions[next_room_id] = new_room_position
        room_assignments[next_room_id] = new_template

        # Mark the new room's connection door as connected.
        # The new room connects via its opposite-facing door (e.g., if we placed
        # a room to the north, it connects via its south door).
        connected_doors.add((next_room_id, direction.opposite()))

        # Add new room's open doors to the queue (except the one we just connected)
        for new_direction in [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]:
            if (next_room_id, new_direction) in connected_doors:
                continue  # This door is already connected

            door_pos = _get_door_position(new_template, new_direction)
            if door_pos:
                open_doors.append(
                    (
                        next_room_id,
                        new_direction,
                        Position(
                            row=new_room_position.row + door_pos.row,
                            column=new_room_position.column + door_pos.column,
                        ),
                    )
                )

        last_room_id = next_room_id
        next_room_id += 1

    # Place goal in the last room added, ensuring it's on a FLOOR tile
    goal_room_id = last_room_id
    goal_pos = room_positions[goal_room_id]
    goal_template = room_assignments[goal_room_id]
    goal_floor_pos = find_floor_tile_in_room(dungeon_map, goal_pos, goal_template)
    dungeon_map[goal_floor_pos.row, goal_floor_pos.column] = Tile.GOAL

    # Replace all unconnected doors with walls
    _replace_blind_doors_with_walls(
        dungeon_map, room_positions, room_assignments, connected_doors
    )

    # Crop the dungeon map to the actual used area
    dungeon_map, crop_offset = _crop_dungeon_map(dungeon_map)

    # Adjust all room positions by the crop offset
    room_positions_adjusted: Dict[int, Position] = {}
    for room_id, pos in room_positions.items():
        room_positions_adjusted[room_id] = Position(
            row=pos.row - crop_offset.row,
            column=pos.column - crop_offset.column,
        )

    # Calculate start position in pixels
    start_room_pos = room_positions_adjusted[start_room_id]
    start_template = room_assignments[start_room_id]
    start_pos = find_floor_tile_in_room(dungeon_map, start_room_pos, start_template)
    start_pos_pixel = (start_pos.column * 64, start_pos.row * 64)

    # Convert Position objects to (tile_x, tile_y) tuples for the return value
    room_positions_final: Dict[int, Tuple[int, int]] = {}
    for room_id, pos in room_positions_adjusted.items():
        room_positions_final[room_id] = (pos.column, pos.row)

    return dungeon_map, start_pos_pixel, room_positions_final, room_assignments
