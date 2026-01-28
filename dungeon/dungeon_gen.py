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
4. Replace all unconnected doors with walls (no "blind doors" that lead nowhere)
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

def left_edge_wall(tile):
    """
    Corners have walls coming out of their edges,
    so in some circumstances they can be treated as
    straight walls to their neighbors.
    """

    if tile in [Tile.NORTH_WALL, Tile.SOUTH_WALL]:
        return tile

    if tile in [Tile.NE_CORNER, Tile.CONVEX_SE]:
        return Tile.NORTH_WALL

    if tile in [Tile.SE_CORNER, Tile.CONVEX_NE]:
        return Tile.SOUTH_WALL

    return None

def right_edge_wall(tile):
    """
    Corners have walls coming out of their edges,
    so in some circumstances they can be treated as
    straight walls to their neighbors.
    """

    if tile in [Tile.NORTH_WALL, Tile.SOUTH_WALL]:
        return tile

    if tile in [Tile.NW_CORNER, Tile.CONVEX_SW]:
        return Tile.NORTH_WALL

    if tile in [Tile.SW_CORNER, Tile.CONVEX_NW]:
        return Tile.SOUTH_WALL

    return None

def top_edge_wall(tile):
    """
    Corners have walls coming out of their edges,
    so in some circumstances they can be treated as
    straight walls to their neighbors.
    """

    if tile in [Tile.EAST_WALL, Tile.WEST_WALL]:
        return tile

    if tile in [Tile.SW_CORNER, Tile.CONVEX_SE]:
        return Tile.WEST_WALL

    if tile in [Tile.SE_CORNER, Tile.CONVEX_SW]:
        return Tile.EAST_WALL

    return None

def bottom_edge_wall(tile):
    """
    Corners have walls coming out of their edges,
    so in some circumstances they can be treated as
    straight walls to their neighbors.
    """

    if tile in [Tile.EAST_WALL, Tile.WEST_WALL]:
        return tile

    if tile in [Tile.NW_CORNER, Tile.CONVEX_NE]:
        return Tile.WEST_WALL

    if tile in [Tile.NE_CORNER, Tile.CONVEX_NW]:
        return Tile.EAST_WALL

    return None

# Use metal labyrinth ASCII mapping
ASCII_TO_TILE = METAL_ASCII_TO_TILE

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

# TODO: let's not assume a single door in each direction.
# instead, let's return a list of doors for each direction,
# or just process all doors in the caller.
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

            # TODO: _has_door assumes one or zero doors per direction,
            # which might be a bad assumption. Instead, scan the rom
            # for door tiles and process each pair that you find.

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

            # For each orientation, replace the door tiles with a straight wall.
            # Replace the tiles that are on either side of the door with tiles
            # that connect to the new walls. 

            if direction == Direction.NORTH:
                # Northern walls need base tiles just to the south of them

                for col_offset in range(2):
                    dungeon_map[door_row, door_col + col_offset] = Tile.NORTH_WALL
                    dungeon_map[door_row + 1, door_col + col_offset] = Tile.NORTH_WALL_BASE

                # Assume that the doorframes are connected correctly to
                # other walls, and maintain those connections when replacing them.
                west_doorframe = dungeon_map[door_row, door_col - 1]
                if left_edge_wall(west_doorframe) == Tile.NORTH_WALL:
                    dungeon_map[door_row, door_col - 1] = Tile.NORTH_WALL
                    dungeon_map[door_row + 1, door_col - 1] = Tile.NORTH_WALL_BASE
                elif bottom_edge_wall(west_doorframe) == Tile.WEST_WALL:
                    dungeon_map[door_row, door_col - 1] = Tile.NW_CORNER

                east_doorframe = dungeon_map[door_row, door_col + 2]
                if right_edge_wall(east_doorframe) == Tile.NORTH_WALL:
                    dungeon_map[door_row, door_col + 2] = Tile.NORTH_WALL
                    dungeon_map[door_row + 1, door_col + 2] = Tile.NORTH_WALL_BASE
                elif bottom_edge_wall(east_doorframe) == Tile.EAST_WALL:
                    dungeon_map[door_row, door_col + 2] = Tile.NE_CORNER


            elif direction == Direction.SOUTH:
                for col_offset in range(2):
                    dungeon_map[door_row, door_col + col_offset] = Tile.SOUTH_WALL

                west_doorframe = dungeon_map[door_row, door_col - 1]
                if left_edge_wall(west_doorframe) == Tile.SOUTH_WALL:
                    dungeon_map[door_row, door_col - 1] = Tile.SOUTH_WALL
                elif top_edge_wall(west_doorframe) == Tile.WEST_WALL: # ?? WRONG
                    dungeon_map[door_row, door_col - 1] = Tile.SW_CORNER

                east_doorframe = dungeon_map[door_row, door_col + 2]
                if right_edge_wall(east_doorframe) == Tile.SOUTH_WALL:
                    dungeon_map[door_row, door_col + 2] = Tile.SOUTH_WALL
                elif top_edge_wall(east_doorframe) == Tile.EAST_WALL: # ??? WRONG?
                    dungeon_map[door_row, door_col + 2] = Tile.SE_CORNER

            elif direction == Direction.EAST:
                for row_offset in range(2):
                    dungeon_map[door_row + row_offset, door_col] = Tile.EAST_WALL

                north_doorframe = dungeon_map[door_row - 1, door_col]
                if top_edge_wall(north_doorframe) == Tile.EAST_WALL:
                    dungeon_map[door_row - 1, door_col] = Tile.EAST_WALL
                elif left_edge_wall(north_doorframe) == Tile.NORTH_WALL:
                    dungeon_map[door_row - 1, door_col] = Tile.NE_CORNER

                bottom_doorframe = dungeon_map[door_row + 2, door_col]
                if bottom_edge_wall(bottom_doorframe) == Tile.EAST_WALL:
                    dungeon_map[door_row + 2, door_col] = Tile.EAST_WALL
                elif left_edge_wall(bottom_doorframe) == Tile.SOUTH_WALL:
                    dungeon_map[door_row + 2, door_col] = Tile.SE_CORNER


            elif direction == Direction.WEST:
                for row_offset in range(2):
                    dungeon_map[door_row + row_offset, door_col] = Tile.WEST_WALL

                north_doorframe = dungeon_map[door_row - 1, door_col]
                if top_edge_wall(north_doorframe) == Tile.WEST_WALL:
                    dungeon_map[door_row - 1, door_col] = Tile.WEST_WALL
                elif right_edge_wall(north_doorframe) == Tile.NORTH_WALL:
                    dungeon_map[door_row - 1, door_col] = Tile.NW_CORNER

                bottom_doorframe = dungeon_map[door_row + 2, door_col]
                if bottom_edge_wall(bottom_doorframe) == Tile.WEST_WALL:
                    dungeon_map[door_row + 2, door_col] = Tile.WEST_WALL
                elif right_edge_wall(bottom_doorframe) == Tile.SOUTH_WALL:
                    dungeon_map[door_row + 2, door_col] = Tile.SW_CORNER



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




def _get_template_by_name(name: str) -> RoomTemplate:
    """Get a room template by name."""
    return next(t for t in ROOM_TEMPLATES if t.name == name)


def create_dungeon_with_gated_goal(
    num_rooms: int,
    max_retries: int = 10,
) -> Tuple["Dungeon", Direction, Position]:
    """
    Create a dungeon with a goal room attached via a single door.

    The goal room is attached to an unconnected north, east, or west door
    from the main dungeon. This creates a setup where the door can be
    blocked by a gate NPC.

    Parameters:
        num_rooms: Target number of rooms in the main dungeon (before goal room)
        max_retries: Maximum attempts to generate a valid dungeon

    Returns:
        Tuple of (dungeon, gate_direction, gate_door_position) where:
        - dungeon: The generated Dungeon with goal placed in the goal room
        - gate_direction: Direction the gate faces (NORTH, EAST, or WEST)
        - gate_door_position: Position of the door tiles (for placing gate NPC)

    Raises:
        RuntimeError: If unable to generate a valid dungeon after max_retries
    """
    from .world import Dungeon

    for _ in range(max_retries):
        # Generate base dungeon layout (without sealing doors or cropping)
        target_num_rooms = num_rooms
        canvas_size = max(2000, target_num_rooms * 100)
        dungeon_map: DungeonMap = np.zeros((canvas_size, canvas_size), dtype=int)

        room_positions: Dict[int, Position] = {}
        room_assignments: Dict[int, RoomTemplate] = {}
        open_doors: List[Tuple[int, Direction, Position]] = []
        connected_doors: Set[Tuple[int, Direction]] = set()

        # Start with first room at center of canvas
        start_room_id = 0
        start_position = Position(row=canvas_size // 2, column=canvas_size // 2)
        start_template = next(t for t in ROOM_TEMPLATES if t.name == "large")

        room_positions[start_room_id] = start_position
        room_assignments[start_room_id] = start_template

        _place_room_on_canvas(dungeon_map, start_template, start_position)

        # Add all doors from the start room to the open doors queue
        for direction in [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]:
            door_pos = _get_door_position(start_template, direction)
            if door_pos:
                open_doors.append((
                    start_room_id,
                    direction,
                    Position(
                        row=start_position.row + door_pos.row,
                        column=start_position.column + door_pos.column,
                    ),
                ))

        # Keep adding rooms until we reach target
        next_room_id = 1

        while len(room_assignments) < target_num_rooms and open_doors:
            random.shuffle(open_doors)
            source_room_id, direction, door_position = open_doors.pop()

            matching_templates = [
                room for room in ROOM_TEMPLATES
                if _has_matching_door(room, direction)
                and room.name not in ("south-only", "west-only", "east-only")
            ]
            if not matching_templates:
                continue

            random.shuffle(matching_templates)

            new_template = None
            for possible_template in matching_templates:
                possible_room_position = _calculate_room_placement(
                    direction, door_position, possible_template
                )
                if not _would_overlap(dungeon_map, possible_template, possible_room_position):
                    new_room_position = possible_room_position
                    new_template = possible_template
                    break

            if not new_template:
                continue

            connected_doors.add((source_room_id, direction))
            _place_room_on_canvas(dungeon_map, new_template, new_room_position)
            room_positions[next_room_id] = new_room_position
            room_assignments[next_room_id] = new_template
            connected_doors.add((next_room_id, direction.opposite()))

            for new_direction in [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]:
                if (next_room_id, new_direction) in connected_doors:
                    continue
                door_pos = _get_door_position(new_template, new_direction)
                if door_pos:
                    open_doors.append((
                        next_room_id,
                        new_direction,
                        Position(
                            row=new_room_position.row + door_pos.row,
                            column=new_room_position.column + door_pos.column,
                        ),
                    ))

            next_room_id += 1

        # Find an unconnected door to attach the goal room chain.
        # The goal is always in a south-only room. We need to connect it via:
        # 1. NORTH door -> attach south-only directly (its SOUTH door connects to NORTH)
        # 2. WEST door -> attach L-shape (WEST entrance, NORTH exit), then south-only to L-shape's NORTH
        # 3. EAST door -> attach J-shape (EAST entrance, NORTH exit), then south-only to J-shape's NORTH

        south_only_template = _get_template_by_name("south-only")

        # Try NORTH doors first (direct attachment)
        attachment_door = None
        for room_id, direction, door_position in open_doors:
            if direction == Direction.NORTH:
                goal_room_position = _calculate_room_placement(
                    direction, door_position, south_only_template
                )
                if not _would_overlap(dungeon_map, south_only_template, goal_room_position):
                    attachment_door = (room_id, direction, door_position)
                    break

        connector_room_id = None
        connector_template = None
        connector_position = None

        if attachment_door is None:
            # Try WEST doors with L-shape connector
            l_shape_template = _get_template_by_name("L-shape")
            for room_id, direction, door_position in open_doors:
                if direction == Direction.WEST:
                    l_shape_position = _calculate_room_placement(
                        direction, door_position, l_shape_template
                    )
                    if _would_overlap(dungeon_map, l_shape_template, l_shape_position):
                        continue
                    # Check if south-only can attach to L-shape's NORTH door
                    l_shape_north_door = _get_door_position(l_shape_template, Direction.NORTH)
                    if l_shape_north_door is None:
                        continue
                    l_shape_north_door_abs = Position(
                        row=l_shape_position.row + l_shape_north_door.row,
                        column=l_shape_position.column + l_shape_north_door.column,
                    )
                    goal_room_position = _calculate_room_placement(
                        Direction.NORTH, l_shape_north_door_abs, south_only_template
                    )
                    if not _would_overlap(dungeon_map, south_only_template, goal_room_position):
                        attachment_door = (room_id, direction, door_position)
                        connector_room_id = next_room_id
                        connector_template = l_shape_template
                        connector_position = l_shape_position
                        break

        if attachment_door is None:
            # Try EAST doors with J-shape connector
            j_shape_template = _get_template_by_name("J-shape")
            for room_id, direction, door_position in open_doors:
                if direction == Direction.EAST:
                    j_shape_position = _calculate_room_placement(
                        direction, door_position, j_shape_template
                    )
                    if _would_overlap(dungeon_map, j_shape_template, j_shape_position):
                        continue
                    # Check if south-only can attach to J-shape's NORTH door
                    j_shape_north_door = _get_door_position(j_shape_template, Direction.NORTH)
                    if j_shape_north_door is None:
                        continue
                    j_shape_north_door_abs = Position(
                        row=j_shape_position.row + j_shape_north_door.row,
                        column=j_shape_position.column + j_shape_north_door.column,
                    )
                    goal_room_position = _calculate_room_placement(
                        Direction.NORTH, j_shape_north_door_abs, south_only_template
                    )
                    if not _would_overlap(dungeon_map, south_only_template, goal_room_position):
                        attachment_door = (room_id, direction, door_position)
                        connector_room_id = next_room_id
                        connector_template = j_shape_template
                        connector_position = j_shape_position
                        break

        if attachment_door is None:
            # No suitable door found, retry
            continue

        source_room_id, direction, door_position = attachment_door

        # Place connector room if needed (L-shape or J-shape)
        if connector_template is not None:
            _place_room_on_canvas(dungeon_map, connector_template, connector_position)
            room_positions[connector_room_id] = connector_position
            room_assignments[connector_room_id] = connector_template
            connected_doors.add((source_room_id, direction))
            connected_doors.add((connector_room_id, direction.opposite()))

            # Update for goal room attachment: attach to connector's NORTH door
            connector_north_door = _get_door_position(connector_template, Direction.NORTH)
            door_position = Position(
                row=connector_position.row + connector_north_door.row,
                column=connector_position.column + connector_north_door.column,
            )
            source_room_id = connector_room_id
            direction = Direction.NORTH
            next_room_id += 1

            # Remove the original attachment door from open_doors
            open_doors = [d for d in open_doors if d != attachment_door]

        # Attach the south-only goal room
        goal_room_position = _calculate_room_placement(direction, door_position, south_only_template)
        _place_room_on_canvas(dungeon_map, south_only_template, goal_room_position)
        goal_room_id = next_room_id
        room_positions[goal_room_id] = goal_room_position
        room_assignments[goal_room_id] = south_only_template

        # Mark doors as connected
        connected_doors.add((source_room_id, direction))
        connected_doors.add((goal_room_id, Direction.SOUTH))  # south-only has SOUTH door

        # Remove the attachment door from open_doors (if not already removed)
        open_doors = [d for d in open_doors if d != attachment_door]

        # The gate position is the SOUTH door of the south-only room
        goal_south_door = _get_door_position(south_only_template, Direction.SOUTH)
        gate_door_position = Position(
            row=goal_room_position.row + goal_south_door.row,
            column=goal_room_position.column + goal_south_door.column,
        )

        # Seal remaining blind doors
        _replace_blind_doors_with_walls(
            dungeon_map, room_positions, room_assignments, connected_doors
        )

        # Crop the dungeon map
        dungeon_map, crop_offset = _crop_dungeon_map(dungeon_map)

        # Adjust all positions by the crop offset
        room_positions_adjusted: Dict[int, Tuple[int, int]] = {}
        for room_id, pos in room_positions.items():
            room_positions_adjusted[room_id] = (
                pos.column - crop_offset.column,
                pos.row - crop_offset.row,
            )

        # Adjust gate door position by crop offset
        adjusted_gate_door_position = Position(
            row=gate_door_position.row - crop_offset.row,
            column=gate_door_position.column - crop_offset.column,
        )

        # Calculate start position
        start_room_pos = room_positions[start_room_id]
        adjusted_start_pos = Position(
            row=start_room_pos.row - crop_offset.row,
            column=start_room_pos.column - crop_offset.column,
        )
        start_pos = find_floor_tile_in_room(dungeon_map, adjusted_start_pos, start_template)
        start_pos_pixel = (start_pos.column * 64, start_pos.row * 64)

        # Create the Dungeon object
        dungeon = Dungeon(
            dungeon_map,
            start_pos_pixel,
            room_positions_adjusted,
            room_assignments,
        )

        # Place the goal in the goal room
        dungeon.place_goal(goal_room_id)

        # Gate always faces SOUTH (blocks the SOUTH door of the south-only room)
        return dungeon, Direction.SOUTH, adjusted_gate_door_position

    raise RuntimeError(
        f"Could not generate dungeon with gated goal after {max_retries} attempts. "
        "No suitable unconnected NORTH, WEST, or EAST door found."
    )
