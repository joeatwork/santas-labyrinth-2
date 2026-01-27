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
from typing import Tuple, List, Dict, Set, Optional, TYPE_CHECKING

from .metal_labyrinth_sprites import (
    MetalTile,
    METAL_ASCII_TO_TILE,
    METAL_ROOM_TEMPLATES,
    MetalRoomTemplate,
)

if TYPE_CHECKING:
    from .world import Dungeon


# Alias MetalTile as Tile for backward compatibility with existing code
Tile = MetalTile

# Use metal labyrinth ASCII mapping
ASCII_TO_TILE = METAL_ASCII_TO_TILE

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


# Alias MetalRoomTemplate as RoomTemplate for backward compatibility
RoomTemplate = MetalRoomTemplate


def _has_door(template: RoomTemplate, direction: "Direction") -> bool:
    """Check if this template has a door in the given direction."""
    door_checks = {
        Direction.NORTH: template.has_north_door,
        Direction.SOUTH: template.has_south_door,
        Direction.EAST: template.has_east_door,
        Direction.WEST: template.has_west_door,
    }
    return door_checks[direction]


def _has_matching_door(template: RoomTemplate, direction: "Direction") -> bool:
    """Check if this template has a door that can connect to the given direction.

    For example, if direction is NORTH (an existing room's north door),
    this returns True if this template has a SOUTH door to connect to it.
    """
    return _has_door(template, direction.opposite())


# Use metal labyrinth room templates
ROOM_TEMPLATES = METAL_ROOM_TEMPLATES


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


def generate_foreground_from_dungeon(dungeon_map: DungeonMap) -> DungeonMap:
    """
    Generates a foreground map from an existing dungeon map.

    Metal labyrinth tileset does not use doorframe foregrounds,
    so this returns an empty map.
    """
    rows, cols = dungeon_map.shape
    return np.zeros((rows, cols), dtype=int)


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

    Also replaces adjacent convex corners with straight walls to maintain
    visual consistency.
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

    # Convex corners that should become walls when adjacent door is removed
    # Maps (direction, side) -> (convex_corner_tile, wall_replacement)
    # For north/south doors: side is 'west' (-1 col) or 'east' (+2 col from door start)
    # For east/west doors: side is 'north' (-1 row) or 'south' (+2 row from door start)
    convex_to_wall = {
        Tile.CONVEX_NE: Tile.NORTH_WALL,  # West of north door -> north wall
        Tile.CONVEX_NW: Tile.NORTH_WALL,  # East of north door -> north wall
        Tile.CONVEX_SE: Tile.SOUTH_WALL,  # West of south door -> south wall
        Tile.CONVEX_SW: Tile.SOUTH_WALL,  # East of south door -> south wall
    }

    # For east/west doors, convex corners become vertical walls
    convex_to_wall_vertical = {
        Tile.CONVEX_SE: Tile.WEST_WALL,  # Above west door -> west wall
        Tile.CONVEX_NE: Tile.WEST_WALL,  # Below west door -> west wall
        Tile.CONVEX_SW: Tile.EAST_WALL,  # Above east door -> east wall
        Tile.CONVEX_NW: Tile.EAST_WALL,  # Below east door -> east wall
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
            if not _has_door(template, direction):
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
                wall_type = Tile.NORTH_WALL if direction == Direction.NORTH else Tile.SOUTH_WALL

                for col_offset in range(2):
                    tile = dungeon_map[door_row, door_col + col_offset]
                    if tile in door_to_wall:
                        dungeon_map[door_row, door_col + col_offset] = door_to_wall[tile]

                # For north doors, replace floor tiles to the south with NORTH_WALL_BASE
                # (north walls need a base tile below them for proper rendering)
                if direction == Direction.NORTH:
                    base_row = door_row + 1
                    if base_row < dungeon_map.shape[0]:
                        for col_offset in range(2):
                            base_tile = dungeon_map[base_row, door_col + col_offset]
                            # Only replace floor-like tiles, not walls or other structures
                            if base_tile == Tile.FLOOR:
                                dungeon_map[base_row, door_col + col_offset] = Tile.NORTH_WALL_BASE

                # Replace convex corners or perpendicular walls on either side of the door
                # West side of door (col - 1)
                west_col = door_col - 1
                if west_col >= 0:
                    west_tile = dungeon_map[door_row, west_col]
                    if west_tile in convex_to_wall:
                        dungeon_map[door_row, west_col] = wall_type
                    elif west_tile == Tile.WEST_WALL:
                        # Perpendicular wall becomes a corner
                        if direction == Direction.NORTH:
                            dungeon_map[door_row, west_col] = Tile.NW_CORNER
                        else:  # Direction.SOUTH
                            dungeon_map[door_row, west_col] = Tile.SW_CORNER

                # East side of door (col + 2, since door is 2 tiles wide)
                east_col = door_col + 2
                if east_col < dungeon_map.shape[1]:
                    east_tile = dungeon_map[door_row, east_col]
                    if east_tile in convex_to_wall:
                        dungeon_map[door_row, east_col] = wall_type
                    elif east_tile == Tile.EAST_WALL:
                        # Perpendicular wall becomes a corner
                        if direction == Direction.NORTH:
                            dungeon_map[door_row, east_col] = Tile.NE_CORNER
                        else:  # Direction.SOUTH
                            dungeon_map[door_row, east_col] = Tile.SE_CORNER
            else:
                # East/West doors are two tiles tall
                wall_type = Tile.WEST_WALL if direction == Direction.WEST else Tile.EAST_WALL

                for row_offset in range(2):
                    tile = dungeon_map[door_row + row_offset, door_col]
                    if tile in door_to_wall:
                        dungeon_map[door_row + row_offset, door_col] = door_to_wall[tile]

                # Replace convex corners or perpendicular walls above and below the door
                # North side of door (row - 1)
                north_row = door_row - 1
                if north_row >= 0:
                    north_tile = dungeon_map[north_row, door_col]
                    if north_tile in convex_to_wall_vertical:
                        dungeon_map[north_row, door_col] = wall_type
                    elif north_tile == Tile.NORTH_WALL:
                        # Perpendicular wall becomes a corner
                        if direction == Direction.WEST:
                            dungeon_map[north_row, door_col] = Tile.NW_CORNER
                        else:  # Direction.EAST
                            dungeon_map[north_row, door_col] = Tile.NE_CORNER

                # South side of door (row + 2, since door is 2 tiles tall)
                south_row = door_row + 2
                if south_row < dungeon_map.shape[0]:
                    south_tile = dungeon_map[south_row, door_col]
                    if south_tile in convex_to_wall_vertical:
                        dungeon_map[south_row, door_col] = wall_type
                    elif south_tile == Tile.SOUTH_WALL:
                        # Perpendicular wall becomes a corner
                        if direction == Direction.WEST:
                            dungeon_map[south_row, door_col] = Tile.SW_CORNER
                        else:  # Direction.EAST
                            dungeon_map[south_row, door_col] = Tile.SE_CORNER


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


def generate_dungeon(
    num_rooms: int,
    place_goal: bool = True,
) -> Tuple[
    DungeonMap,
    Tuple[int, int],
    Dict[int, Tuple[int, int]],
    Dict[int, RoomTemplate],
    Optional[int],
]:
    """
    Generates a dungeon by organically growing rooms from open doors.

    Uses the ultra-simple algorithm documented at the top of this file.

    Parameters:
        num_rooms: Target number of rooms to generate
        place_goal: If True, return the last_room_id for goal placement.
                    If False, no goal room is returned (can be placed later via Dungeon.place_goal()).

    Returns:
        dungeon_map: The tile map
        start_pos_pixel: Starting position in pixels
        room_positions: Dict mapping room_id to (tile_x, tile_y) position
        room_assignments: Dict mapping room_id to RoomTemplate used
        goal_room_id: The room_id where the goal should be placed (if place_goal=True), else None
    """
    target_num_rooms = num_rooms

    # We'll use a much larger canvas to avoid worrying about bounds initially
    # TODO: create this canvas after choosing all rooms layout so you know
    # in advance the actual size of the dungeon
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
    # Always use the "large" room template as the first room to ensure
    # we have at least one room with a 4x4 walkable area for NPC placement
    start_room_id = 0
    start_position = Position(row=canvas_size // 2, column=canvas_size // 2)
    start_template = next(t for t in ROOM_TEMPLATES if t.name == "large")

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
            room for room in ROOM_TEMPLATES if _has_matching_door(room, direction)
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

        # TODO: rather than record doors as room_id, direction
        # let's record the doors with their north-westernmost
        # tile. That way, a room can have multiple north doors.

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

    # Determine goal room (last room added)
    goal_room_id: Optional[int] = last_room_id if place_goal else None

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

    return dungeon_map, start_pos_pixel, room_positions_final, room_assignments, goal_room_id


def create_random_dungeon(
    num_rooms: int,
    place_goal: bool = True,
) -> "Dungeon":
    """
    Factory function to create a randomly generated dungeon.

    Parameters:
        num_rooms: Target number of rooms to generate
        place_goal: If True, place the goal NPC in the last room.
                    If False, no goal is placed (can be added later via Dungeon.place_goal()).

    Returns:
        A Dungeon instance with the generated map and layout
    """
    from .world import Dungeon

    dungeon_map, start_pos, room_positions, room_templates, goal_room_id = generate_dungeon(
        num_rooms, place_goal=place_goal
    )
    dungeon = Dungeon(dungeon_map, start_pos, room_positions, room_templates)

    # Place goal NPC if requested
    if goal_room_id is not None:
        dungeon.place_goal(goal_room_id)

    return dungeon
